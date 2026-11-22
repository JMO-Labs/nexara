"""
@file test_chore_service.py
@brief Unit tests for chore rotation: next_due, set_schedule, advance, recap.
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import AppError, AuthorizationError, ValidationError
from app.models.community import Community
from app.models.list import List, ListItem
from app.models.list_assignment import ListItemAssignment
from app.repositories.chore_repo import ChoreRepository
from app.repositories.list_assignment_repo import ListAssignmentRepository
from app.repositories.list_item_repo import ListItemRepository
from app.repositories.list_repo import ListRepository
from app.services import recap_sections
from app.services.chore_service import ChoreService, next_due
from app.services.list_activity_service import ListActivityService

CID = uuid.uuid4()
NOW = datetime(2026, 11, 22, 12, 0, tzinfo=UTC)
A, B, C = (uuid.uuid4() for _ in range(3))


def _build(rotation=(A, B, C), index=0, completed=False, active=A, usable=None, features=None):
    comm = MagicMock(spec=Community)
    comm.id, comm.features = CID, features or {}
    lst = MagicMock(spec=List)
    lst.id, lst.owner_id, lst.title = uuid.uuid4(), uuid.uuid4(), "Chores"
    item = MagicMock(spec=ListItem)
    item.id, item.list_id, item.values = uuid.uuid4(), lst.id, {"title": "Trash"}
    item.repeat, item.rotation, item.rotation_index = "weekly", list(rotation), index
    item.completed, item.next_due_at = completed, NOW - timedelta(minutes=1)
    repo = AsyncMock(spec=ChoreRepository)
    repo.usable_users.side_effect = lambda ids, _o: (
        set(ids) if usable is None else set(ids) & usable
    )
    items = AsyncMock(spec=ListItemRepository)
    items.lock_item_for_update.return_value = item
    items.update.side_effect = lambda i, d: [setattr(i, k, v) for k, v in d.items()] and i
    lists = AsyncMock(spec=ListRepository)
    lists.get_by_id.return_value = lst
    lists.can_view.return_value = True
    assign = AsyncMock(spec=ListAssignmentRepository)
    cur = None
    if active:
        cur = MagicMock(spec=ListItemAssignment)
        cur.assignee_id = active
    assign.get_active.return_value = cur
    act = AsyncMock(spec=ListActivityService)
    notify = AsyncMock()
    svc = ChoreService(repo, items, lists, assign, act, comm, notify)
    return svc, item, lst, repo, assign, act, notify, lists


def test_next_due_clamps_month_end():
    assert next_due(datetime(2027, 1, 31, tzinfo=UTC), "monthly") == datetime(
        2027, 2, 28, tzinfo=UTC
    )
    assert next_due(datetime(2028, 1, 31, tzinfo=UTC), "monthly") == datetime(
        2028, 2, 29, tzinfo=UTC
    )
    assert next_due(datetime(2026, 12, 15, tzinfo=UTC), "monthly") == datetime(
        2027, 1, 15, tzinfo=UTC
    )
    assert next_due(NOW, "daily") - NOW == timedelta(days=1)
    assert next_due(NOW, "weekly") - NOW == timedelta(days=7)


async def test_advance_missed_assigns_next_and_notifies():
    svc, item, lst, _repo, assign, act, notify, _ = _build()
    due = item.next_due_at
    await svc.advance(item, NOW)
    assert act.record.await_args_list[0].args[2] == "missed"
    assert act.record.await_args_list[0].args[5] == A
    assign.remove.assert_awaited_once()
    assert assign.add.await_args.args[3] == B
    assert assign.add.await_args.args[5] == "pending"
    assert item.rotation_index == 1
    assert item.next_due_at == due + timedelta(days=7)
    assert notify.notify.await_args.args[:2] == (B, "list_assigned")


async def test_advance_completed_not_missed_and_reopens():
    svc, item, _lst, repo, _assign, act, _n, lists = _build(completed=True)
    item.values = {"title": "Trash", "_completed_by": "x"}
    await svc.advance(item, NOW)
    assert all(c.args[2] != "missed" for c in act.record.await_args_list)
    assert item.completed is False and "_completed_by" not in item.values
    repo.clear_completions.assert_awaited_once()
    lists.increment_counters.assert_awaited_once()


async def test_advance_skips_ineligible_members():
    svc, item, *_rest = _build(usable={A, C})
    assign = _rest[2]
    await svc.advance(item, NOW)
    assert assign.add.await_args.args[3] == C and item.rotation_index == 2


async def test_advance_skips_users_no_longer_on_list():
    svc, item, _lst, _repo, assign, _act, _n, lists = _build()
    lists.can_view.side_effect = lambda _l, u: u != B
    await svc.advance(item, NOW)
    assert assign.add.await_args.args[3] == C


async def test_advance_wraps_and_single_member_keeps_turn():
    svc, item, _l, _r, assign, *_ = _build(index=2)
    await svc.advance(item, NOW)
    assert assign.add.await_args.args[3] == A and item.rotation_index == 0
    svc, item, _l, _r, assign, *_ = _build(usable={A})
    await svc.advance(item, NOW)
    assert assign.add.await_args.args[3] == A


async def test_advance_nobody_eligible_only_moves_date():
    svc, item, _l, _r, assign, *_ = _build(usable=set())
    await svc.advance(item, NOW)
    assign.add.assert_not_awaited()
    assert item.next_due_at > NOW


async def test_advance_twice_is_one_advance():
    svc, item, _l, _r, assign, *_ = _build()
    await svc.advance(item, NOW)
    await svc.advance(item, NOW)
    assert assign.add.await_count == 1


async def test_advance_catches_up_after_downtime():
    svc, item, *_ = _build()
    item.next_due_at = NOW - timedelta(days=30)
    await svc.advance(item, NOW)
    assert NOW < item.next_due_at <= NOW + timedelta(days=7)


async def test_set_schedule_validates_members_and_flag_and_owner():
    svc, item, lst, repo, assign, _a, _n, _l = _build(rotation=(), active=None)
    item.repeat = None
    repo.usable_users.side_effect = lambda ids, _o: set(ids) - {C}
    with pytest.raises(ValidationError):
        await svc.set_schedule(lst.id, item.id, lst.owner_id, "weekly", [A, C], NOW)
    with pytest.raises(AuthorizationError):
        await svc.set_schedule(lst.id, item.id, uuid.uuid4(), "weekly", [A], NOW)
    with pytest.raises(ValidationError):
        await svc.set_schedule(lst.id, item.id, lst.owner_id, None, [A], NOW)
    await svc.set_schedule(lst.id, item.id, lst.owner_id, "weekly", [A, B, A], NOW)
    assert item.rotation == [A, B] and item.rotation_index == 0
    assert item.next_due_at == NOW + timedelta(days=7)
    assert assign.add.await_args.args[3] == A
    off, *_ = _build(features={"chores": False})
    with pytest.raises(AppError):
        await off.set_schedule(lst.id, item.id, lst.owner_id, "daily", [], NOW)


async def test_set_schedule_clear_resets():
    svc, item, lst, *_ = _build()
    await svc.set_schedule(lst.id, item.id, lst.owner_id, None, [], NOW)
    assert item.repeat is None and item.rotation == [] and item.next_due_at is None


async def test_recap_my_chores_flag_and_visibility():
    svc, item, lst, *_ = _build()
    user = MagicMock()
    user.id = A
    ctx = recap_sections.RecapContext(user, svc._community, MagicMock(), NOW, NOW.date(), "UTC")
    with (
        patch("app.services.recap_sections.ChoreRepository") as cr,
        patch("app.services.recap_sections.ListRepository") as ok,
    ):
        ok.return_value.can_view = AsyncMock(return_value=True)
        cr.return_value.assigned_chores = AsyncMock(return_value=[(item, lst)])
        sec = await recap_sections.my_chores(ctx)
        assert sec is not None and sec["title"] == "Your chores this week"
        assert sec["items"][0]["text"].startswith("Trash (Chores)")
        with patch("app.services.recap_sections.ListRepository") as lr:
            lr.return_value.can_view = AsyncMock(return_value=False)
            hidden = await recap_sections.my_chores(ctx)
        assert hidden is not None and hidden["items"] == []
        ctx.community.features = {"chores": False}
        assert await recap_sections.my_chores(ctx) is None
