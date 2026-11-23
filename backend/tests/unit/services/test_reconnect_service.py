"""
@file test_reconnect_service.py
@brief Unit tests for ReconnectService orchestration (queries are covered by the
       real-Postgres test in tests/integration/repositories/test_reconnect_pick.py).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import AppError
from app.models.community import Community
from app.models.user import User
from app.repositories.community_repo import CommunityRepository
from app.repositories.reconnect_repo import ReconnectRepository
from app.repositories.user_repo import UserRepository
from app.services.notification_service import NotificationService
from app.services.notifications import registry
from app.services.reconnect_service import ReconnectService

CID = uuid.uuid4()
NOW = datetime(2026, 11, 22, 15, tzinfo=UTC)


def _svc(features: dict | None = None):
    repo = AsyncMock(spec=ReconnectRepository)
    repo.prefs.return_value = (True, 30)
    repo.has_recent_reconnect.return_value = False
    users = AsyncMock(spec=UserRepository)
    comm = AsyncMock(spec=CommunityRepository)
    comm.get.return_value = MagicMock(spec=Community, features=features or {})
    notif = AsyncMock(spec=NotificationService)
    return ReconnectService(repo, users, comm, notif, CID), repo, users, notif


async def test_pick_uses_user_days_cutoff():
    svc, repo, *_ = _svc()
    repo.prefs.return_value = (True, 60)
    rel = uuid.uuid4()
    repo.stalest_relative.return_value = rel
    uid = uuid.uuid4()
    assert await svc.pick(uid, NOW) == rel
    assert repo.stalest_relative.await_args.args[2] == NOW - timedelta(days=60)


@pytest.mark.parametrize("prefs,recent", [((False, 30), False), ((True, 30), True)])
async def test_pick_none_when_opted_out_or_recent(prefs, recent):
    svc, repo, *_ = _svc()
    repo.prefs.return_value = prefs
    repo.has_recent_reconnect.return_value = recent
    assert await svc.pick(uuid.uuid4(), NOW) is None
    repo.stalest_relative.assert_not_awaited()


async def test_run_notifies_with_dm_link_and_records():
    svc, repo, users, notif = _svc()
    uid, tid = uuid.uuid4(), uuid.uuid4()
    repo.eligible_users.return_value = [uid]
    repo.stalest_relative.return_value = tid
    users.get_by_id.return_value = MagicMock(spec=User, id=tid, display_name="Dana")
    assert await svc.run(NOW) == 1
    repo.record.assert_awaited_once_with(uid, CID, NOW)
    args = notif.notify.await_args.args
    assert args[0] == uid and args[1] == "reconnect"
    assert args[2]["link"] == f"/app/chat?dm={tid}" and args[2]["target_id"] == str(tid)


async def test_run_skips_when_flag_off():
    svc, repo, _, notif = _svc({"reconnect_nudges": False})
    assert await svc.run(NOW) == 0
    repo.eligible_users.assert_not_awaited()
    notif.notify.assert_not_awaited()


async def test_snooze_rejects_self_and_flag_off():
    svc, *_ = _svc()
    uid = uuid.uuid4()
    with pytest.raises(AppError):
        await svc.snooze(uid, uid, NOW)
    off, *_ = _svc({"reconnect_nudges": False})
    with pytest.raises(AppError):
        await off.snooze(uid, uuid.uuid4(), NOW)


def test_type_registered_with_snooze_action_and_pref_map():
    from app.services.notification_service import PREF_MAP

    t = registry.get("reconnect")
    assert t.actions[0].url_template.startswith("/api/v1/reconnect/snooze")
    assert "reconnect" in PREF_MAP


def test_beat_daily_at_15_utc():
    import app.tasks.nudge_tasks  # noqa: F401
    from app.tasks.celery_app import celery_app

    e = celery_app.conf.beat_schedule["nudges-reconnect"]
    assert e["task"] == "nudges.reconnect" and e["schedule"].hour == {15}
    assert "nudges.reconnect" in celery_app.tasks
