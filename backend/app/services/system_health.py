"""
@file system_health.py
@brief Collects component health, disk and runtime facts for the admin System page.

Every probe is isolated: a failing dependency yields a ``down`` component, never an
exception. Output carries no secrets or connection strings.
"""

from __future__ import annotations

import asyncio
import shutil
import time
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import psutil
import structlog
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.valkey import DB_BROKER, DB_CACHE, get_pool
from app.repositories.system_repo import SystemRepository
from app.schemas.admin_system import Component, DiskInfo, RuntimeInfo, SystemHealth, TableSize

logger = structlog.get_logger(__name__)

QUEUES = ("default", "maintenance", "notifications", "email", "media")
DB_WARN_SECONDS = 0.2
QUEUE_WARN = 100
BEAT_WARN = timedelta(minutes=10)
DISK_ALERT_PCT = 85.0
CACHE_SECONDS = 10
WORKER_HEARTBEAT_KEY = "health:worker_heartbeat"
HEARTBEAT_STALE = timedelta(minutes=12)
OVERALL_TIMEOUT = 5.0
T_DB, T_VALKEY, T_WORKERS, T_QUEUES, T_DISK = 2.0, 1.0, 3.0, 1.0, 2.0
PING_TIMEOUT = 1.0
_STARTED = time.time()
# ponytail: per-process cache is enough for 10 s of admin polling; no shared store.
_cache: tuple[float, SystemHealth] | None = None
_lock = asyncio.Lock()
psutil.cpu_percent(None)  # prime: first call is meaningless


def grafana_link(settings: Settings) -> str | None:
    """@brief Configured ``GRAFANA_URL`` when it is http(s), else None."""
    url = (getattr(settings, "GRAFANA_URL", "") or "").strip()
    return url if url.lower().startswith(("http://", "https://")) else None


def app_version(settings: Settings) -> str:
    """@brief Release version from ``settings.APP_VERSION`` (images carry no package metadata)."""
    return settings.APP_VERSION or "unknown"


def _timed_out(name: str) -> Component:
    return Component(name=name, status="down", detail="Timed out")


async def _database(session: AsyncSession) -> Component:
    t0 = time.perf_counter()
    try:
        await SystemRepository(session).ping()
    except Exception:
        return Component(name="database", status="down", detail="Unreachable")
    dt = time.perf_counter() - t0
    return Component(
        name="database",
        status="warn" if dt > DB_WARN_SECONDS else "ok",
        detail=f"{dt * 1000:.0f} ms",
    )


async def _valkey(cache: Redis) -> Component:
    try:
        await cache.ping()
    except Exception:
        return Component(name="valkey", status="down", detail="Unreachable")
    return Component(name="valkey", status="ok")


def _ping_workers() -> dict[str, Any]:
    """@brief Broadcast ping; bounded connect (1 s, one retry) so threads cannot pile up."""
    from app.tasks.celery_app import celery_app

    with celery_app.connection_for_write(connect_timeout=PING_TIMEOUT) as conn:
        conn.ensure_connection(max_retries=1)
        return celery_app.control.inspect(timeout=PING_TIMEOUT, connection=conn).ping() or {}


async def _ping_once() -> dict[str, Any]:
    try:
        return await asyncio.to_thread(_ping_workers)
    except Exception:
        return {}


def heartbeat_age(raw: str | bytes | None, now: datetime | None = None) -> timedelta | None:
    """@brief Age of a stored unix-timestamp heartbeat, or None if absent/garbled."""
    if not raw:
        return None
    try:
        ts = datetime.fromtimestamp(float(raw), UTC)
    except (ValueError, OSError):
        return None
    return (now or datetime.now(UTC)) - ts


async def _workers(cache: Redis) -> Component:
    """
    @brief ``down`` when two pings get no reply; the heartbeat age is detail text only.

    (The heartbeat drives the API watchdog's ``worker_down`` alert, not this status.)
    """
    pong = await _ping_once() or await _ping_once()
    if pong:
        return Component(name="workers", status="ok", detail=f"{len(pong)} online")
    try:
        age = heartbeat_age(await cache.get(WORKER_HEARTBEAT_KEY))
    except Exception:
        age = None
    detail = "No workers responding"
    if age is not None:
        detail += f"; last heartbeat {int(age.total_seconds() // 60)} min ago"
    return Component(name="workers", status="down", detail=detail)


async def _queues(broker: Redis) -> Component:
    try:
        depths = {q: int(await broker.llen(q)) for q in QUEUES}  # type: ignore[misc]
    except Exception:
        return Component(name="queues", status="down", detail="Unavailable")
    detail = ", ".join(f"{q} {n}" for q, n in depths.items())
    deep = any(n > QUEUE_WARN for n in depths.values())
    return Component(name="queues", status="warn" if deep else "ok", detail=detail)


async def _beat(cache: Redis) -> Component:
    try:
        raw = await cache.get("beat:last_run")
    except Exception:
        return Component(name="beat", status="down", detail="Unavailable")
    age = heartbeat_age(raw)
    if age is None:
        return Component(name="beat", status="warn", detail="No heartbeat yet")
    mins = int(age.total_seconds() // 60)
    return Component(
        name="beat", status="warn" if age > BEAT_WARN else "ok", detail=f"{mins} min ago"
    )


async def smtp_state(
    session: AsyncSession, community_id: uuid.UUID
) -> tuple[datetime | None, str | None]:
    """@brief ``(smtp_last_ok_at, smtp_last_error)`` for the community (error clears on success)."""
    return await SystemRepository(session).smtp_state(community_id)


async def _email(session: AsyncSession, community_id: uuid.UUID) -> Component:
    try:
        ok_at, err = await smtp_state(session, community_id)
    except Exception:
        return Component(name="email", status="down", detail="Unavailable")
    if err:
        # smtp_last_error is a sanitised "category: fixed message" (see email/sender.py).
        return Component(name="email", status="warn", detail=err[:200])
    if ok_at is None:
        return Component(name="email", status="ok", detail="No mail sent yet")
    return Component(name="email", status="ok", detail=f"Last sent {ok_at:%Y-%m-%d %H:%M} UTC")


def _push(settings: Settings) -> Component:
    if settings.VAPID_PUBLIC_KEY and settings.VAPID_PRIVATE_KEY:
        return Component(name="push", status="ok")
    return Component(name="push", status="warn", detail="Not set up")


async def _disk(session: AsyncSession, settings: Settings) -> DiskInfo:
    info = DiskInfo(external=settings.STORAGE_BACKEND.lower() != "local")
    if not info.external:
        try:
            u = shutil.disk_usage(Path(settings.LOCAL_STORAGE_PATH))
            info.total_bytes, info.used_bytes = u.total, u.used
            info.used_pct = round(u.used / u.total * 100, 1) if u.total else None
        except OSError:
            logger.warning("system_health.disk_unavailable")
    try:
        info.db_bytes, top = await SystemRepository(session).sizes()
        info.top_tables = [TableSize(name=n, bytes=b) for n, b in top]
    except Exception:
        logger.warning("system_health.db_size_unavailable")
    return info


def _read_int(path: str) -> int | None:
    try:
        raw = Path(path).read_text().strip()
        return None if raw == "max" else int(raw)
    except (OSError, ValueError):
        return None


def _cgroup_limit() -> int | None:
    return _read_int("/sys/fs/cgroup/memory.max")


async def _runtime(session: AsyncSession, settings: Settings) -> RuntimeInfo:
    head: str | None
    try:
        head = await SystemRepository(session).alembic_head()
    except Exception:
        head = None
    mem = psutil.virtual_memory()
    limit = _cgroup_limit()
    used = mem.used
    if limit is not None and (cur := _read_int("/sys/fs/cgroup/memory.current")) is not None:
        used = cur  # container view when running under a cgroup limit
    return RuntimeInfo(
        version=app_version(settings),
        alembic_head=head,
        uptime_seconds=int(time.time() - _STARTED),
        cpu_percent=psutil.cpu_percent(None),
        mem_total_bytes=limit or mem.total,
        mem_used_bytes=used,
        mem_limit_bytes=limit,
    )


async def collect(
    session: AsyncSession,
    settings: Settings,
    cache: Redis | None = None,
    broker: Redis | None = None,
) -> SystemHealth:
    """
    @brief Gather a full health snapshot concurrently; never raises on dependency failure.

    Each probe is bounded (DB 2 s, Valkey 1 s, workers 3 s, queues 1 s) and the whole
    call is capped at 5 s; a timed-out probe reports ``down`` / ``Timed out``. DB
    probes share one session so they are serialised by a lock, each in a savepoint.

    @param session DB session.
    @param settings Application settings.
    @param cache Valkey cache client (default: shared pool; tasks pass their own).
    @param broker Valkey broker client (default: shared pool).
    @return Components, disk and runtime info.
    """
    cache = cache or get_pool(settings, DB_CACHE)
    broker = broker or get_pool(settings, DB_BROKER)
    cid = uuid.UUID(settings.COMMUNITY_ID)
    dblock = asyncio.Lock()

    async def bounded(
        coro: Awaitable[Any], limit: float, fallback: Any, locked: bool = False
    ) -> Any:
        try:
            if locked:
                async with dblock:
                    return await asyncio.wait_for(coro, limit)
            return await asyncio.wait_for(coro, limit)
        except Exception:  # incl. TimeoutError
            return fallback

    fb: Callable[[str], Component] = _timed_out
    names = ["database", "valkey", "workers", "queues", "beat", "email"]
    jobs = [
        bounded(_database(session), T_DB, fb("database"), True),
        bounded(_valkey(cache), T_VALKEY, fb("valkey")),
        bounded(_workers(cache), T_WORKERS, fb("workers")),
        bounded(_queues(broker), T_QUEUES, fb("queues")),
        bounded(_beat(cache), T_VALKEY, fb("beat")),
        bounded(_email(session, cid), T_DB, fb("email"), True),
        bounded(
            _disk(session, settings),
            T_DISK,
            DiskInfo(external=settings.STORAGE_BACKEND.lower() != "local"),
            True,
        ),
        bounded(_runtime(session, settings), T_DISK, None, True),
    ]
    tasks = [asyncio.ensure_future(j) for j in jobs]
    _, pending = await asyncio.wait(tasks, timeout=OVERALL_TIMEOUT)
    for t in pending:
        t.cancel()
    if pending:  # let cancelled savepoints unwind before the caller reuses the session
        await asyncio.gather(*pending, return_exceptions=True)
    results = [t.result() if t in tasks and not t.cancelled() and t.done() else None for t in tasks]
    comps = [r if r is not None else fb(n) for n, r in zip(names, results[:6], strict=True)]
    comps.insert(6, _push(settings))
    disk = results[6] or DiskInfo(external=settings.STORAGE_BACKEND.lower() != "local")
    runtime = results[7] or RuntimeInfo(
        version=app_version(settings),
        uptime_seconds=int(time.time() - _STARTED),
        cpu_percent=0.0,
        mem_total_bytes=0,
        mem_used_bytes=0,
    )
    return SystemHealth(
        components=comps, disk=disk, runtime=runtime, grafana_url=grafana_link(settings)
    )


async def collect_cached(session: AsyncSession, settings: Settings) -> SystemHealth:
    """@brief :func:`collect` memoised for 10 s per process (one refresh at a time)."""
    global _cache
    if _cache and time.monotonic() - _cache[0] < CACHE_SECONDS:
        return _cache[1]
    async with _lock:
        if _cache and time.monotonic() - _cache[0] < CACHE_SECONDS:
            return _cache[1]
        health = await collect(session, settings)
        _cache = (time.monotonic(), health)
        return health
