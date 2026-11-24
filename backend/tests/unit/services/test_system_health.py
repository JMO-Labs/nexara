"""
@file test_system_health.py
@brief Unit tests for the health collector and health_tasks alerts.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.schemas.admin_system import Component, DiskInfo, RuntimeInfo, SystemHealth
from app.services import system_health as sh

CID = "00000000-0000-0000-0000-000000000001"


def _settings(**kw):
    base = dict(
        COMMUNITY_ID=CID,
        VAPID_PUBLIC_KEY="",
        VAPID_PRIVATE_KEY="",
        STORAGE_BACKEND="local",
        LOCAL_STORAGE_PATH="/tmp",
    )
    return SimpleNamespace(**{**base, **kw})


async def test_valkey_down_is_component_down() -> None:
    redis = MagicMock()
    redis.ping = AsyncMock(side_effect=OSError("down"))
    c = await sh._valkey(redis)
    assert c.status == "down"
    assert "redis://" not in c.detail


async def test_queues_warn_over_100() -> None:
    redis = MagicMock()
    redis.llen = AsyncMock(side_effect=[0, 101, 0, 0, 0])
    c = await sh._queues(redis)
    assert c.status == "warn"


async def test_push_not_set_up_warns() -> None:
    assert sh._push(_settings()).status == "warn"
    assert sh._push(_settings(VAPID_PUBLIC_KEY="a", VAPID_PRIVATE_KEY="b")).status == "ok"


async def test_workers_none_is_down() -> None:
    redis = MagicMock()
    redis.get = AsyncMock(return_value=None)
    with patch.object(sh, "_ping_workers", return_value={}):
        assert (await sh._workers(redis)).status == "down"
        redis.get = AsyncMock(return_value=str(__import__("time").time() - 60))
        assert (await sh._workers(redis)).status == "warn"  # heartbeat fallback


async def test_beat_missing_warns_and_stale_warns() -> None:
    import time

    redis = MagicMock()
    redis.get = AsyncMock(return_value=None)
    assert (await sh._beat(redis)).status == "warn"
    redis.get = AsyncMock(return_value=str(time.time() - 3600))
    assert (await sh._beat(redis)).status == "warn"
    redis.get = AsyncMock(return_value=str(time.time() - 60))
    assert (await sh._beat(redis)).status == "ok"


async def test_email_error_warns() -> None:
    with patch.object(sh, "smtp_state", AsyncMock(return_value=(None, "auth: bad"))):
        assert (await sh._email(MagicMock(), uuid.uuid4())).status == "warn"


def _health(pct, workers="ok") -> SystemHealth:
    return SystemHealth(
        components=[Component(name="workers", status=workers)],
        disk=DiskInfo(external=False, used_pct=pct),
        runtime=RuntimeInfo(
            version="x",
            uptime_seconds=1,
            cpu_percent=0,
            mem_total_bytes=1,
            mem_used_bytes=1,
        ),
    )


async def _run_check(health, err=None):
    from app.tasks import health_tasks as ht

    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    session.commit = AsyncMock()
    alert = AsyncMock()
    redis = MagicMock()
    redis.set = AsyncMock()
    redis.aclose = AsyncMock()
    with (
        patch.object(ht, "async_session_factory", return_value=session),
        patch.object(ht.system_health, "collect", AsyncMock(return_value=health)),
        patch.object(ht.system_health, "smtp_state", AsyncMock(return_value=(None, err))),
        patch.object(ht, "admin_alert", alert),
        patch.object(ht, "create_pool", return_value=redis),
        patch.object(ht, "get_settings", return_value=_settings()),
    ):
        fired = await ht._check_async()
    return fired, alert, redis


async def test_disk_90_alerts_once() -> None:
    fired, alert, redis = await _run_check(_health(90.0))
    assert fired == ["disk_high"]
    alert.assert_awaited_once()
    assert alert.await_args.args[2] == "disk_high"
    keys = [c.args[0] for c in redis.set.await_args_list]
    assert keys == ["beat:last_run", "health:worker_heartbeat"]
    assert redis.aclose.await_count == 2  # per-task clients closed
    from app.tasks import health_tasks as ht

    assert not hasattr(ht, "get_pool")  # never the shared loop-bound pool


async def test_healthy_no_alert_and_worker_email_alerts() -> None:
    fired, alert, _ = await _run_check(_health(50.0))
    assert fired == []
    fired, alert, _ = await _run_check(_health(None, "down"), err="x")
    assert fired == ["worker_down", "email_failing"]


def _ok_redis():
    r = MagicMock()
    r.ping = AsyncMock()
    r.get = AsyncMock(return_value=None)
    r.llen = AsyncMock(return_value=0)
    return r


def _session(fail_first=False):
    s = MagicMock()
    calls = {"n": 0}

    def begin_nested():
        calls["n"] += 1
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=None)
        cm.__aexit__ = AsyncMock(return_value=False)
        return cm

    async def execute(*a, **k):
        if fail_first and calls["n"] == 1:
            raise RuntimeError("db boom")
        r = MagicMock()
        r.first.return_value = (None, None)
        r.scalar.return_value = "0073"
        r.scalar_one.return_value = 1
        r.__iter__ = lambda self: iter([])
        return r

    s.begin_nested = begin_nested
    s.execute = execute
    return s


async def test_db_probe_failure_only_marks_db_down() -> None:
    with patch.object(sh, "_ping_workers", return_value={"w": 1}):
        h = await sh.collect(_session(fail_first=True), _settings(), _ok_redis(), _ok_redis())
    c = {x.name: x.status for x in h.components}
    assert c["database"] == "down"
    assert c["valkey"] == c["workers"] == c["queues"] == "ok"
    assert c["email"] == "ok"


async def test_valkey_hang_is_bounded() -> None:
    import asyncio
    import time

    hang = _ok_redis()

    async def never(*a, **k):
        await asyncio.sleep(60)

    hang.ping = never
    t0 = time.monotonic()
    with patch.object(sh, "_ping_workers", return_value={"w": 1}):
        h = await sh.collect(_session(), _settings(), hang, _ok_redis())
    assert time.monotonic() - t0 < 5
    v = next(x for x in h.components if x.name == "valkey")
    assert (v.status, v.detail) == ("down", "Timed out")
