"""
@file test_memories_service.py
@brief Unit tests for memory_day, local-date logic and the daily reminder.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import AppError
from app.models.community import Community
from app.models.user import User
from app.repositories.community_repo import CommunityRepository
from app.repositories.post_memories_repo import PostMemoriesRepository
from app.repositories.user_repo import UserRepository
from app.services.memories_service import MemoriesService, local_today, memory_day
from app.services.notification_service import NotificationService

CID = uuid.uuid4()


def test_memory_day_non_leap_feb_28_includes_29():
    assert memory_day(date(2027, 2, 28)) == [(2, 28), (2, 29)]


def test_memory_day_leap_feb_28_only():
    assert memory_day(date(2028, 2, 28)) == [(2, 28)]


def test_memory_day_plain():
    assert memory_day(date(2026, 11, 22)) == [(11, 22)]


def test_local_today_honolulu():
    now = datetime(2026, 11, 23, 5, 0, tzinfo=UTC)
    assert local_today("Pacific/Honolulu", now) == date(2026, 11, 22)
    assert local_today(None, now) == date(2026, 11, 23)
    assert local_today("Bogus/Zone", now) == date(2026, 11, 23)


def _svc(*, tz: str | None = "Pacific/Honolulu", enabled: bool = True):
    repo = AsyncMock(spec=PostMemoriesRepository)
    users = AsyncMock(spec=UserRepository)
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.timezone = tz
    users.get_by_id.return_value = user
    comms = AsyncMock(spec=CommunityRepository)
    comm = MagicMock(spec=Community)
    comm.features = {} if enabled else {"on_this_day": False}
    comms.get.return_value = comm
    notif = AsyncMock(spec=NotificationService)
    svc = MemoriesService(repo, users, comms, CID, notif)
    return svc, repo, user, notif


async def test_on_this_day_uses_viewer_local_date():
    svc, repo, user, _ = _svc()
    repo.on_this_day.return_value = [
        {"id": "p1", "created_at": "2025-11-22T20:00:00+00:00"},
    ]
    now = datetime(2026, 11, 23, 5, 0, tzinfo=UTC)
    out = await svc.on_this_day(user.id, now=now)
    args = repo.on_this_day.await_args
    assert (args.args[2], args.args[3], args.args[4]) == (11, 22, 2026)
    assert out["years_ago"] == [1]
    assert len(out["items"]) == 1


async def test_on_this_day_feature_off_raises():
    svc, _, user, _ = _svc(enabled=False)
    with pytest.raises(AppError) as ei:
        await svc.on_this_day(user.id)
    assert ei.value.status_code == 404


async def test_notify_due_fires_once_per_window():
    svc, repo, user, notif = _svc(tz="UTC")
    repo.list_user_tz.return_value = [(user.id, "UTC")]
    repo.on_this_day.return_value = [{"id": "p", "created_at": "2025-11-22T09:00:00+00:00"}]
    sent: set[uuid.UUID] = set()

    async def notified(_cid, ids, _since):
        return sent & set(ids)

    async def notify(uid, *_a, **_k):
        sent.add(uid)

    repo.notified_since.side_effect = notified
    notif.notify.side_effect = notify
    now = datetime(2026, 11, 22, 9, 5, tzinfo=UTC)
    assert await svc.notify_due(now=now) == 1
    assert await svc.notify_due(now=now) == 0
    notif.notify.assert_awaited_once()
    assert notif.notify.await_args.args[1] == "on_this_day"


async def test_notify_due_skips_wrong_hour_and_empty():
    svc, repo, user, notif = _svc(tz="UTC")
    repo.list_user_tz.return_value = [(user.id, "UTC")]
    repo.notified_since.return_value = set()
    repo.on_this_day.return_value = []
    assert await svc.notify_due(now=datetime(2026, 11, 22, 10, 5, tzinfo=UTC)) == 0
    assert await svc.notify_due(now=datetime(2026, 11, 22, 9, 5, tzinfo=UTC)) == 0
    notif.notify.assert_not_awaited()
