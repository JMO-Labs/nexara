"""
@file test_list_completion_service.py
@brief Unit tests for ListCompletionService (shared and per_user modes).
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import AppError, NotFoundError
from app.models.list import List, ListItem
from app.repositories.list_completion_repo import ListCompletionRepository
from app.repositories.list_item_repo import ListItemRepository
from app.repositories.list_repo import ListRepository
from app.services.list_completion_service import ListCompletionService
from app.services.list_field_registry import ListFieldRegistry
from app.services.realtime.events import CommunityTarget, UserTarget

CID = uuid.UUID("00000000-0000-0000-0000-000000000001")
OWNER = uuid.uuid4()
USER = uuid.uuid4()


def _setup(
    mode: str | None,
    *,
    completed: bool = False,
    existing: bool = False,
    visibility: str = "community",
    can_view: bool = True,
):
    cfg = {} if mode is None else {"completion_mode": mode}
    lst = MagicMock(spec=List)
    lst.id, lst.owner_id, lst.title = uuid.uuid4(), OWNER, "Groceries"
    lst.field_schema = [{"key": "done", "type": "checkbox", "config": cfg}]
    item = MagicMock(spec=ListItem)
    item.id, item.list_id, item.completed, item.values = uuid.uuid4(), lst.id, completed, {}
    items = AsyncMock(spec=ListItemRepository)
    items.lock_item_for_update.return_value = item
    items.update.side_effect = lambda e, d: [setattr(e, k, v) for k, v in d.items()] and e
    lst.visibility = visibility
    lists = AsyncMock(spec=ListRepository)
    lists.get_by_id.return_value = lst
    lists.can_view.return_value = can_view
    lists.audience_ids.return_value = {OWNER, USER}
    comps = AsyncMock(spec=ListCompletionRepository)
    comps.get_completion.return_value = MagicMock() if existing else None
    comps.delete_completion.return_value = existing
    comps.count_for_item.return_value = 1 if existing else 0
    bus, notif = AsyncMock(), AsyncMock()
    svc = ListCompletionService(
        items, lists, comps, ListFieldRegistry(), bus, notif, community_id=CID
    )
    return svc, item, lists, comps, bus, notif


def test_mode_defaults_to_shared():
    svc = _setup(None)[0]
    schema = [{"key": "done", "type": "checkbox", "config": {}}]
    assert svc._get_completion_mode(schema, "done") == "shared"
    assert svc._get_completion_mode(schema, None) == "shared"


class TestShared:
    async def test_complete_sets_flag(self):
        svc, item, lists, comps, bus, notif = _setup("shared")
        await svc.complete_item(item.id, USER)
        assert item.completed is True
        assert item.values["_completed_by"] == str(USER)
        comps.create_completion.assert_not_called()
        lists.increment_counters.assert_awaited_once_with(item.list_id, {"completed_count": 1})
        evt = bus.emit.await_args.args[0]
        assert evt.payload["completion_mode"] == "shared"
        assert evt.payload["event"] == "list.completed"
        notif.notify.assert_awaited_once()

    async def test_already_completed_is_noop(self):
        svc, item, lists, _, bus, notif = _setup("shared", completed=True)
        await svc.complete_item(item.id, USER)
        lists.increment_counters.assert_not_called()
        bus.emit.assert_not_called()
        notif.notify.assert_not_called()

    async def test_owner_not_notified_of_own_action(self):
        svc, item, _, _, bus, notif = _setup("shared")
        await svc.complete_item(item.id, OWNER)
        notif.notify.assert_not_called()
        bus.emit.assert_awaited_once()

    async def test_uncomplete(self):
        svc, item, lists, _, bus, _ = _setup("shared", completed=True)
        await svc.uncomplete_item(item.id, USER)
        assert item.completed is False
        assert "_completed_by" not in item.values
        lists.increment_counters.assert_awaited_once_with(item.list_id, {"completed_count": -1})
        assert bus.emit.await_args.args[0].payload["event"] == "list.uncompleted"


class TestPerUser:
    async def test_complete_creates_row(self):
        svc, item, lists, comps, bus, notif = _setup("per_user")
        await svc.complete_item(item.id, USER)
        comps.create_completion.assert_awaited_once_with(item.id, USER)
        assert item.completed is True  # at least one user completed
        lists.increment_counters.assert_awaited_once_with(item.list_id, {"completed_count": 1})
        assert bus.emit.await_args.args[0].payload["completion_mode"] == "per_user"
        notif.notify.assert_awaited_once()

    async def test_second_user_does_not_bump_counter(self):
        svc, item, lists, comps, _, _ = _setup("per_user", completed=True)
        await svc.complete_item(item.id, USER)
        comps.create_completion.assert_awaited_once()
        lists.increment_counters.assert_not_called()

    async def test_duplicate_completion_is_noop(self):
        svc, item, _, comps, bus, _ = _setup("per_user", existing=True)
        await svc.complete_item(item.id, USER)
        comps.create_completion.assert_not_called()
        bus.emit.assert_not_called()

    async def test_uncomplete_last_user_clears_flag(self):
        svc, item, lists, comps, bus, _ = _setup("per_user", completed=True, existing=True)
        comps.count_for_item.return_value = 0
        await svc.uncomplete_item(item.id, USER)
        comps.delete_completion.assert_awaited_once_with(item.id, USER)
        assert item.completed is False
        lists.increment_counters.assert_awaited_once_with(item.list_id, {"completed_count": -1})
        assert bus.emit.await_args.args[0].payload["completion_mode"] == "per_user"

    async def test_uncomplete_with_others_keeps_flag(self):
        svc, item, lists, comps, _, _ = _setup("per_user", completed=True, existing=True)
        comps.count_for_item.return_value = 1
        await svc.uncomplete_item(item.id, USER)
        assert item.completed is True
        lists.increment_counters.assert_not_called()

    async def test_uncomplete_without_row_is_noop(self):
        svc, item, _, comps, bus, _ = _setup("per_user", completed=True)
        await svc.uncomplete_item(item.id, USER)
        bus.emit.assert_not_called()


async def test_missing_item_raises():
    svc, item, *_ = _setup("shared")
    svc._items.lock_item_for_update.return_value = None
    with pytest.raises(NotFoundError):
        await svc.complete_item(item.id, USER)


async def test_unknown_field_key_raises():
    svc, item, *_ = _setup("shared")
    with pytest.raises(AppError):
        await svc.complete_item(item.id, USER, field_key="nope")


class TestAccess:
    async def test_private_list_non_owner_cannot_complete(self):
        svc, item, lists, _, bus, _ = _setup("shared", visibility="private", can_view=False)
        with pytest.raises(NotFoundError):
            await svc.complete_item(item.id, USER)
        lists.increment_counters.assert_not_called()
        bus.emit.assert_not_called()

    async def test_subgroup_list_non_member_cannot_uncomplete(self):
        svc, item, _, _, bus, _ = _setup(
            "shared", completed=True, visibility="subgroup", can_view=False
        )
        with pytest.raises(NotFoundError):
            await svc.uncomplete_item(item.id, USER)
        bus.emit.assert_not_called()

    async def test_view_check_uses_acting_user(self):
        svc, item, lists, *_ = _setup("shared")
        await svc.complete_item(item.id, USER)
        lists.can_view.assert_awaited_once()
        assert lists.can_view.await_args.args[1] == USER

    async def test_private_list_events_not_community_wide(self):
        svc, item, _, _, bus, _ = _setup("shared", visibility="private")
        await svc.complete_item(item.id, USER)
        targets = [c.args[0].target for c in bus.emit.await_args_list]
        assert targets and all(isinstance(t, UserTarget) for t in targets)
        assert {t.user_id for t in targets} == {OWNER, USER}

    async def test_community_list_event_is_community_wide(self):
        svc, item, _, _, bus, _ = _setup("shared")
        await svc.complete_item(item.id, USER)
        assert isinstance(bus.emit.await_args.args[0].target, CommunityTarget)
