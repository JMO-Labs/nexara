"""@file Tests for ListItemService validation, projection and counters."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import AuthorizationError, NotFoundError, ValidationError
from app.models.list import List, ListItem
from app.repositories.list_item_repo import ListItemRepository
from app.repositories.list_repo import ListRepository
from app.services.list_field_registry import ListFieldRegistry
from app.services.list_items_service import ListItemService

SCHEMA = [
    {"key": "due", "type_key": "date", "config": {"is_due_field": True}},
    {"key": "where", "type_key": "location", "config": {}},
]


@pytest.fixture
def lst():
    m = MagicMock(spec=List)
    m.id = uuid.uuid4()
    m.owner_id = uuid.uuid4()
    m.visibility = "community"
    m.subgroup_id = None
    m.field_schema = SCHEMA
    return m


@pytest.fixture
def svc(lst):
    items = AsyncMock(spec=ListItemRepository)
    lists = AsyncMock(spec=ListRepository)
    lists.get_by_id.return_value = lst
    reg = MagicMock(spec=ListFieldRegistry)
    reg.validate_value.side_effect = lambda k, v, c: v
    due = datetime(2026, 1, 1, tzinfo=UTC)
    reg.project_columns.side_effect = lambda k, v, c: (
        {"due_at": due} if k == "date" and v else {"lat": 1.0, "lon": 2.0} if k == "location" else {}
    )
    items.create.side_effect = lambda e: e
    items.update.side_effect = lambda e, d: [setattr(e, k, v) for k, v in d.items()] and e
    return ListItemService(items, lists, reg), items, lists, reg


async def test_list_items_uses_keyset(svc, lst):
    s, items, _, _ = svc
    items.list_items_keyset.return_value = ([], None)
    out = await s.list_items(lst.id, uuid.uuid4(), cursor="c", limit=10)
    assert out == ([], None)
    items.list_items_keyset.assert_awaited_once_with(lst.id, "c", 10, "position")


async def test_list_items_private_denied(svc, lst):
    s, *_ = svc
    lst.visibility = "private"
    with pytest.raises(AuthorizationError):
        await s.list_items(lst.id, uuid.uuid4())


async def test_list_items_missing_list(svc, lst):
    s, _, lists, _ = svc
    lists.get_by_id.return_value = None
    with pytest.raises(NotFoundError):
        await s.list_items(lst.id, uuid.uuid4())


async def test_create_validates_projects_increments(svc, lst):
    s, items, lists, reg = svc
    item = await s.create(lst.id, lst.owner_id, {"due": "x", "where": "y"})
    assert reg.validate_value.call_count == 2
    assert item.due_at is not None and item.lat == 1.0 and item.lon == 2.0
    lists.increment_counters.assert_awaited_once_with(lst.id, {"item_count": 1})


async def test_create_invalid_value(svc, lst):
    s, items, lists, reg = svc
    reg.validate_value.side_effect = ValueError("bad")
    with pytest.raises(ValidationError):
        await s.create(lst.id, lst.owner_id, {"due": "x"})
    items.create.assert_not_awaited()


async def test_create_unknown_key_rejected(svc, lst):
    s, *_ = svc
    with pytest.raises(ValidationError):
        await s.create(lst.id, lst.owner_id, {"zzz": 1})


def test_project_item_merges_columns(svc, lst):
    s, *_ = svc
    item = MagicMock(spec=ListItem)
    item.values = {"due": "x", "where": "y"}
    cols = s._project_item(lst, item)
    assert set(cols) == {"due_at", "lat", "lon"}


async def test_update_reprojects(svc, lst):
    s, items, _, reg = svc
    item = MagicMock(spec=ListItem)
    item.id, item.list_id, item.values = uuid.uuid4(), lst.id, {}
    items.get_by_id.return_value = item
    await s.update(item.id, lst.owner_id, {"where": "y"})
    assert item.lat == 1.0


async def test_delete_decrements(svc, lst):
    s, items, lists, _ = svc
    item = MagicMock(spec=ListItem)
    item.id, item.list_id, item.completed = uuid.uuid4(), lst.id, False
    items.get_by_id.return_value = item
    await s.delete(item.id, lst.owner_id)
    items.soft_delete.assert_awaited_once_with(item)
    lists.increment_counters.assert_awaited_once_with(lst.id, {"item_count": -1})


async def test_delete_completed_decrements_completed(svc, lst):
    s, items, lists, _ = svc
    item = MagicMock(spec=ListItem)
    item.id, item.list_id, item.completed = uuid.uuid4(), lst.id, True
    items.get_by_id.return_value = item
    await s.delete(item.id, lst.owner_id)
    lists.increment_counters.assert_awaited_once_with(
        lst.id, {"item_count": -1, "completed_count": -1}
    )


async def test_sync_counters_updates_list(svc, lst):
    s, _, lists, _ = svc
    res = MagicMock()
    res.one.return_value = (3, 2)
    lists.session = MagicMock()
    lists.session.execute = AsyncMock(return_value=res)
    await s._sync_item_counters(lst)
    lists.update.assert_awaited_once_with(lst, {"item_count": 3, "completed_count": 2})
