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
from datetime import UTC, datetime, timedelta
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

import psutil
import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.valkey import DB_BROKER, DB_CACHE, get_pool
from app.schemas.admin_system import Component, DiskInfo, RuntimeInfo, SystemHealth, TableSize

logger = structlog.get_logger(__name__)

QUEUES = ("default", "maintenance", "notifications", "email", "media")
DB_WARN_SECONDS = 0.2
QUEUE_WARN = 100
BEAT_WARN = timedelta(minutes=10)
DISK_ALERT_PCT = 85.0
CACHE_SECONDS = 10
_STARTED = time.time()
# ponytail: per-process cache is enough for 10 s of admin polling; no shared store.
_cache: tuple[float, SystemHealth] | None = None


def app_version() -> str:
    """@brief Backend package version (``unknown`` when not installed)."""
    try:
        return version("nexara-backend")
    except PackageNotFoundError:
        return "unknown"


async def _database(session: AsyncSession) -> Component:
    t0 = time.perf_counter()
    try:
        await session.execute(text("select 1"))
    except Exception:
        return Component(name="database", status="down", detail="Unreachable")
    dt = time.perf_counter() - t0
    return Component(
        name="database",
        status="warn" if dt > DB_WARN_SECONDS else "ok",
        detail=f"{dt * 1000:.0f} ms",
    )


async def _valkey(settings: Settings) -> Component:
    try:
        await get_pool(settings, DB_CACHE).ping()
    except Exception:
        return Component(name="valkey", status="down", detail="Unreachable")
    return Component(name="valkey", status="ok")


def _ping_workers() -> dict[str, Any]:
    from app.tasks.celery_app import celery_app

    return celery_app.control.inspect(timeout=1).ping() or {}


async def _workers() -> Component:
    try:
        pong = await asyncio.to_thread(_ping_workers)
    except Exception:
        pong = {}
    if not pong:
        return Component(name="workers", status="down", detail="No workers responding")
    return Component(name="workers", status="ok", detail=f"{len(pong)} online")


async def _queues(settings: Settings) -> Component:
    try:
        redis = get_pool(settings, DB_BROKER)
        depths = {q: int(await redis.llen(q)) for q in QUEUES}  # type: ignore[misc]
    except Exception:
        return Component(name="queues", status="down", detail="Unavailable")
    detail = ", ".join(f"{q} {n}" for q, n in depths.items())
    deep = any(n > QUEUE_WARN for n in depths.values())
    return Component(name="queues", status="warn" if deep else "ok", detail=detail)


async def _beat(settings: Settings) -> Component:
    try:
        raw = await get_pool(settings, DB_CACHE).get("beat:last_run")
    except Exception:
        return Component(name="beat", status="down", detail="Unavailable")
    if not raw:
        return Component(name="beat", status="warn", detail="No heartbeat yet")
    age = datetime.now(UTC) - datetime.fromtimestamp(float(raw), UTC)
    mins = int(age.total_seconds() // 60)
    return Component(
        name="beat", status="warn" if age > BEAT_WARN else "ok", detail=f"{mins} min ago"
    )


async def smtp_state(
    session: AsyncSession, community_id: uuid.UUID
) -> tuple[datetime | None, str | None]:
    """@brief ``(smtp_last_ok_at, smtp_last_error)`` for the community (error clears on success)."""
    row = (
        await session.execute(
            text("select smtp_last_ok_at, smtp_last_error from communities where id = :cid"),
            {"cid": community_id},
        )
    ).first()
    return (row[0], row[1]) if row else (None, None)


async def _email(session: AsyncSession, community_id: uuid.UUID) -> Component:
    try:
        ok_at, err = await smtp_state(session, community_id)
    except Exception:
        return Component(name="email", status="down", detail="Unavailable")
    if err:
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
        info.db_bytes = int(
            (
                await session.execute(text("select pg_database_size(current_database())"))
            ).scalar_one()
        )
        rows = await session.execute(
            text(
                "select relname, pg_total_relation_size(c.oid) from pg_class c "
                "join pg_namespace n on n.oid = c.relnamespace "
                "where c.relkind = 'r' and n.nspname = 'public' "
                "order by 2 desc limit 10"
            )
        )
        info.top_tables = [TableSize(name=r[0], bytes=int(r[1])) for r in rows]
    except Exception:
        logger.warning("system_health.db_size_unavailable")
    return info


def _cgroup_limit() -> int | None:
    try:
        raw = Path("/sys/fs/cgroup/memory.max").read_text().strip()
        return None if raw == "max" else int(raw)
    except (OSError, ValueError):
        return None


async def _runtime(session: AsyncSession) -> RuntimeInfo:
    head: str | None
    try:
        head = (await session.execute(text("select version_num from alembic_version"))).scalar()
    except Exception:
        head = None
    mem = psutil.virtual_memory()
    return RuntimeInfo(
        version=app_version(),
        alembic_head=head,
        uptime_seconds=int(time.time() - _STARTED),
        cpu_percent=psutil.cpu_percent(None),
        mem_total_bytes=mem.total,
        mem_used_bytes=mem.used,
        mem_limit_bytes=_cgroup_limit(),
    )


async def collect(session: AsyncSession, settings: Settings) -> SystemHealth:
    """
    @brief Gather a full health snapshot; never raises on dependency failure.

    @param session DB session.
    @param settings Application settings.
    @return Components, disk and runtime info.
    """
    cid = uuid.UUID(settings.COMMUNITY_ID)
    components = [
        await _database(session),
        await _valkey(settings),
        await _workers(),
        await _queues(settings),
        await _beat(settings),
        await _email(session, cid),
        _push(settings),
    ]
    return SystemHealth(
        components=components,
        disk=await _disk(session, settings),
        runtime=await _runtime(session),
    )


async def collect_cached(session: AsyncSession, settings: Settings) -> SystemHealth:
    """@brief :func:`collect` memoised for 10 s per process."""
    global _cache
    if _cache and time.monotonic() - _cache[0] < CACHE_SECONDS:
        return _cache[1]
    health = await collect(session, settings)
    _cache = (time.monotonic(), health)
    return health
