"""
@file test_chore_tasks.py
@brief Tests for the chores.advance_due beat task.
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from celery.schedules import crontab

from app.tasks import chore_tasks
from app.tasks.celery_app import celery_app

NOW = datetime(2026, 11, 22, 12, 0, tzinfo=UTC)


def test_beat_schedule_and_route():
    entry = celery_app.conf.beat_schedule["chores-advance-due"]
    assert entry["task"] == "chores.advance_due"
    assert entry["schedule"] == crontab(minute="*/15")
    assert celery_app.amqp.router.route({}, "chores.advance_due")["queue"].name == "maintenance"


def _session(community):
    session = AsyncMock()
    lst = MagicMock(community_id=community.id)
    session.get.side_effect = lambda model, _id: lst if model.__name__ == "List" else community
    return session


async def test_advance_due_skips_flag_off_and_locked_rows():
    on = MagicMock(id=uuid.uuid4(), features={})
    off = MagicMock(id=uuid.uuid4(), features={"chores": False})
    ids = [uuid.uuid4(), uuid.uuid4()]
    for community, expected in ((on, 1), (off, 0)):
        session = _session(community)
        svc = MagicMock()
        svc.enabled.return_value = community is on
        svc.advance = AsyncMock()
        with (
            patch.object(chore_tasks, "ChoreRepository") as repo,
            patch.object(chore_tasks, "_service", return_value=svc),
        ):
            repo.return_value.due_item_ids = AsyncMock(return_value=ids)
            repo.return_value.lock_due = AsyncMock(side_effect=[MagicMock(), None])
            assert await chore_tasks.advance_due(session, NOW) == expected
        assert svc.advance.await_count == expected


async def test_advance_failure_rolls_back_and_continues():
    community = MagicMock(id=uuid.uuid4(), features={})
    session = _session(community)
    svc = MagicMock()
    svc.enabled.return_value = True
    svc.advance = AsyncMock(side_effect=[RuntimeError("x"), None])
    with (
        patch.object(chore_tasks, "ChoreRepository") as repo,
        patch.object(chore_tasks, "_service", return_value=svc),
    ):
        repo.return_value.due_item_ids = AsyncMock(return_value=[uuid.uuid4(), uuid.uuid4()])
        repo.return_value.lock_due = AsyncMock(side_effect=[MagicMock(), MagicMock()])
        assert await chore_tasks.advance_due(session, NOW) == 1
    session.rollback.assert_awaited_once()
