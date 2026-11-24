"""
@file test_admin_alerts.py
@brief admin_alert dedupe client choice and inline vs queued Apprise delivery.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from app.services import admin_alerts as aa

CID = uuid.UUID("00000000-0000-0000-0000-000000000001")


async def _alert(kind: str, redis=None):
    deliver = AsyncMock()
    delay = MagicMock()
    users = MagicMock()
    users.admin_ids = AsyncMock(return_value=[])
    with (
        patch.object(aa, "deliver_apprise", deliver),
        patch("app.tasks.admin_alert_tasks.send_apprise_alert.delay", delay),
        patch.object(aa, "UserRepository", return_value=users),
        patch.object(aa, "build_notification_service", return_value=MagicMock()),
        patch.object(aa, "get_pool") as pool,
    ):
        await aa.admin_alert(MagicMock(), CID, kind, {}, redis)
    return deliver, delay, pool


def _redis(first: bool = True) -> MagicMock:
    r = MagicMock()
    r.set = AsyncMock(return_value=first)
    return r


async def test_worker_down_delivers_apprise_inline() -> None:
    deliver, delay, _ = await _alert("worker_down", _redis())
    deliver.assert_awaited_once()
    assert deliver.await_args.args[2] == "A background worker is down"
    delay.assert_not_called()


async def test_other_kinds_queue_to_celery() -> None:
    deliver, delay, _ = await _alert("disk_high", _redis())
    deliver.assert_not_awaited()
    delay.assert_called_once_with(str(CID), "Disk usage is high")


async def test_passed_client_used_for_dedupe_not_shared_pool() -> None:
    r = _redis(first=False)  # already sent within the window
    deliver, delay, pool = await _alert("disk_high", r)
    pool.assert_not_called()
    r.set.assert_awaited_once()
    deliver.assert_not_awaited()
    delay.assert_not_called()
