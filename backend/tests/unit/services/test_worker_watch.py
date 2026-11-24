"""
@file test_worker_watch.py
@brief Heartbeat staleness logic and one watchdog tick.
"""

from __future__ import annotations

import time
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.services import worker_watch as ww


def test_heartbeat_stale_logic() -> None:
    now = time.time()
    assert not ww.heartbeat_stale(str(now - 60), timedelta(0))
    assert ww.heartbeat_stale(str(now - 13 * 60), timedelta(0))
    assert not ww.heartbeat_stale(None, timedelta(minutes=5))  # fresh install
    assert ww.heartbeat_stale(None, timedelta(minutes=13))


async def _tick(raw, started):
    redis = MagicMock()
    redis.get = AsyncMock(return_value=raw)
    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    session.commit = AsyncMock()
    alert = AsyncMock()
    with (
        patch.object(ww, "get_pool", return_value=redis),
        patch.object(ww, "async_session_factory", return_value=session),
        patch.object(ww, "admin_alert", alert),
    ):
        return await ww.tick(started), alert


async def test_tick_alerts_when_stale() -> None:
    fired, alert = await _tick(str(time.time() - 3600), time.monotonic())
    assert fired
    assert alert.await_args.args[2] == "worker_down"


async def test_tick_quiet_when_fresh_or_valkey_down() -> None:
    fired, alert = await _tick(str(time.time()), time.monotonic())
    assert not fired
    alert.assert_not_awaited()
    redis = MagicMock()
    redis.get = AsyncMock(side_effect=OSError)
    with patch.object(ww, "get_pool", return_value=redis):
        assert await ww.tick(time.monotonic()) is False


async def test_watchdog_alert_sends_apprise_inline_not_via_celery() -> None:
    from app.services import admin_alerts as aa

    redis = MagicMock()
    redis.get = AsyncMock(return_value=str(time.time() - 3600))
    redis.set = AsyncMock(return_value=True)
    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    session.commit = AsyncMock()
    users = MagicMock()
    users.admin_ids = AsyncMock(return_value=[])
    deliver, delay = AsyncMock(), MagicMock()
    with (
        patch.object(ww, "get_pool", return_value=redis),
        patch.object(aa, "get_pool", return_value=redis),
        patch.object(ww, "async_session_factory", return_value=session),
        patch.object(aa, "deliver_apprise", deliver),
        patch.object(aa, "UserRepository", return_value=users),
        patch.object(aa, "build_notification_service", return_value=MagicMock()),
        patch("app.tasks.admin_alert_tasks.send_apprise_alert.delay", delay),
    ):
        assert await ww.tick(time.monotonic())
    deliver.assert_awaited_once()
    delay.assert_not_called()
