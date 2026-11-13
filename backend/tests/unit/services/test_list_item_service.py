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
from app.services.list_field_types import registry as real_registry
from app.services.list_items_service import ListItemService

SCHEMA = [
    {"key": "due", "type_key": "date", "config": {"is_due_field": True}},
    {"key": "where", "type_key": "location", "config": {}},
    {"key": "slot", "type_key": "signup", "config": {"default_quantity_needed": 3}},
]
CID = uuid.uuid4()


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
        {"due_at": due}
        if k == "date" and v
        else {"lat": 1.0, "lon": 2.0}
        if k == "location" and v
        else {"signup_quantity_needed": 3}
        if k == "signup"
        else {}
    )
    items.create.side_effect = lambda e: e
    items.update.side_effect = lambda e, d: [setattr(e, k, v) for k, v in d.items()] and e
    return ListItemService(items, lists, reg), items, lists, reg


async def test_list_items_uses_keyset(svc, lst):
    s, items, _, _ = svc
    items.list_items_keyset.return_value = ([], None)
    out = await s.list_items(CID, lst.id, uuid.uuid4(), cursor="c", limit=10)
    assert out == ([], None)
    items.list_items_keyset.assert_awaited_once_with(lst.id, "c", 10, "position")


async def test_list_items_private_denied(svc, lst):
    s, *_ = svc
    lst.visibility = "private"
    with pytest.raises(AuthorizationError):
        await s.list_items(CID, lst.id, uuid.uuid4())


async def test_list_items_missing_list(svc, lst):
    s, _, lists, _ = svc
    lists.get_by_id.return_value = None
    with pytest.raises(NotFoundError):
        await s.list_items(CID, lst.id, uuid.uuid4())


async def test_create_validates_projects_increments(svc, lst):
    s, items, lists, reg = svc
    item = await s.create(CID, lst.id, lst.owner_id, {"due": "x", "where": "y", "slot": 1})
    assert reg.validate_value.call_count == 3
    assert item.signup_quantity_needed == 3
    assert item.due_at is not None and item.lat == 1.0 and item.lon == 2.0
    lists.increment_counters.assert_awaited_once_with(lst.id, {"item_count": 1})


async def test_create_invalid_value(svc, lst):
    s, items, lists, reg = svc
    reg.validate_value.side_effect = ValueError("bad")
    with pytest.raises(ValidationError):
        await s.create(CID, lst.id, lst.owner_id, {"due": "x"})
    items.create.assert_not_awaited()


async def test_create_unknown_key_rejected(svc, lst):
    s, *_ = svc
    with pytest.raises(ValidationError):
        await s.create(CID, lst.id, lst.owner_id, {"zzz": 1})


def test_project_item_merges_columns(svc, lst):
    s, *_ = svc
    item = MagicMock(spec=ListItem)
    item.values = {"due": "x", "where": "y", "slot": 1}
    cols = s._project_item(lst, item)
    assert set(cols) == {"due_at", "lat", "lon", "signup_quantity_needed"}


async def test_update_reprojects(svc, lst):
    s, items, _, reg = svc
    item = MagicMock(spec=ListItem)
    item.id, item.list_id, item.values = uuid.uuid4(), lst.id, {}
    items.get_by_id.return_value = item
    await s.update(CID, item.id, lst.owner_id, {"where": "y"})
    assert item.lat == 1.0


async def test_delete_decrements(svc, lst):
    s, items, lists, _ = svc
    item = MagicMock(spec=ListItem)
    item.id, item.list_id, item.completed = uuid.uuid4(), lst.id, False
    items.get_by_id.return_value = item
    await s.delete(CID, item.id, lst.owner_id)
    items.soft_delete.assert_awaited_once_with(item)
    lists.increment_counters.assert_awaited_once_with(lst.id, {"item_count": -1})


async def test_delete_completed_decrements_completed(svc, lst):
    s, items, lists, _ = svc
    item = MagicMock(spec=ListItem)
    item.id, item.list_id, item.completed = uuid.uuid4(), lst.id, True
    items.get_by_id.return_value = item
    await s.delete(CID, item.id, lst.owner_id)
    lists.increment_counters.assert_awaited_once_with(
        lst.id, {"item_count": -1, "completed_count": -1}
    )


async def test_sync_counters_updates_list(svc, lst):
    s, items, lists, _ = svc
    items.count_live_and_completed.return_value = (3, 2)
    await s.sync_item_counters(lst)
    lists.update.assert_awaited_once_with(lst, {"item_count": 3, "completed_count": 2})


async def test_update_clearing_location_nulls_hot_columns(svc, lst):
    s, items, _, _ = svc
    item = MagicMock(spec=ListItem)
    item.id, item.list_id = uuid.uuid4(), lst.id
    item.values, item.lat, item.lon = {"where": {"lat": 1.0, "lon": 2.0}}, 1.0, 2.0
    items.get_by_id.return_value = item
    await s.update(CID, item.id, lst.owner_id, {"where": None})
    assert item.lat is None and item.lon is None


async def test_scoped_to_community(svc, lst):
    s, items, lists, _ = svc
    await s.list_items(CID, lst.id, uuid.uuid4())
    lists.get_by_id.assert_awaited_with(lst.id, CID)
    lists.get_by_id.return_value = None
    item = MagicMock(spec=ListItem)
    item.list_id = lst.id
    items.get_by_id.return_value = item
    with pytest.raises(NotFoundError):
        await s.delete(CID, uuid.uuid4(), lst.owner_id)


async def test_members_visibility_uses_repo(svc, lst):
    s, items, lists, _ = svc
    lst.visibility = "members"
    items.list_items_keyset.return_value = ([], None)
    lists.is_member.return_value = False
    with pytest.raises(AuthorizationError):
        await s.list_items(CID, lst.id, uuid.uuid4())
    lists.is_member.return_value = True
    await s.list_items(CID, lst.id, uuid.uuid4())


async def test_create_with_real_registry_optional_fields_omitted(lst):
    items = AsyncMock(spec=ListItemRepository)
    lists = AsyncMock(spec=ListRepository)
    lists.get_by_id.return_value = lst
    items.create.side_effect = lambda e: e
    s = ListItemService(items, lists, real_registry)
    item = await s.create(CID, lst.id, lst.owner_id, {"where": {"lat": 1, "lon": 2}})
    assert item.values == {"where": {"lat": 1.0, "lon": 2.0}}
    assert item.due_at is None and item.lat == 1.0


async def test_owner_can_view_private_list(svc, lst):
    s, items, _, _ = svc
    lst.visibility = "private"
    items.list_items_keyset.return_value = ([], None)
    assert await s.list_items(CID, lst.id, lst.owner_id) == ([], None)


async def test_subgroup_visibility(svc, lst):
    s, items, _, _ = svc
    sg = uuid.uuid4()
    lst.visibility, lst.subgroup_id = "subgroup", sg
    items.list_items_keyset.return_value = ([], None)
    with pytest.raises(AuthorizationError):
        await s.list_items(CID, lst.id, uuid.uuid4(), subgroup_ids=None)
    with pytest.raises(AuthorizationError):
        await s.list_items(CID, lst.id, uuid.uuid4(), subgroup_ids=[uuid.uuid4()])
    lst.subgroup_id = None
    with pytest.raises(AuthorizationError):
        await s.list_items(CID, lst.id, uuid.uuid4(), subgroup_ids=[sg])
    lst.subgroup_id = sg
    assert await s.list_items(CID, lst.id, uuid.uuid4(), subgroup_ids=[sg]) == ([], None)


async def test_missing_item_not_found(svc):
    s, items, _, _ = svc
    items.get_by_id.return_value = None
    with pytest.raises(NotFoundError):
        await s.update(CID, uuid.uuid4(), uuid.uuid4(), {})


async def test_list_items_bad_cursor_is_validation_error(svc, lst):
    s, items, _, _ = svc
    items.list_items_keyset.side_effect = ValueError("bad cursor")
    with pytest.raises(ValidationError, match="bad cursor"):
        await s.list_items(CID, lst.id, uuid.uuid4(), cursor="zzz")


async def test_create_non_owner_denied(svc, lst):
    s, items, lists, _ = svc
    with pytest.raises(AuthorizationError):
        await s.create(CID, lst.id, uuid.uuid4(), {})
    items.create.assert_not_awaited()
    lists.increment_counters.assert_not_awaited()


async def test_update_and_delete_non_owner_denied(svc, lst):
    s, items, lists, _ = svc
    item = MagicMock(spec=ListItem)
    item.id, item.list_id, item.values = uuid.uuid4(), lst.id, {}
    items.get_by_id.return_value = item
    other = uuid.uuid4()
    with pytest.raises(AuthorizationError):
        await s.update(CID, item.id, other, {"where": "y"})
    with pytest.raises(AuthorizationError):
        await s.delete(CID, item.id, other)
    items.update.assert_not_awaited()
    items.soft_delete.assert_not_awaited()
    lists.increment_counters.assert_not_awaited()


async def test_create_notifies_audience_except_adder(lst):
    from app.services.notification_service import NotificationService

    items = AsyncMock(spec=ListItemRepository)
    lists = AsyncMock(spec=ListRepository)
    lists.get_by_id.return_value = lst
    member = uuid.uuid4()
    lists.audience_ids.return_value = {member, lst.owner_id}
    items.create.side_effect = lambda e: setattr(e, "id", uuid.uuid4()) or e
    reg = MagicMock(spec=ListFieldRegistry)
    reg.validate_value.side_effect = lambda k, v, c: v
    reg.project_columns.return_value = {}
    notif = AsyncMock(spec=NotificationService)
    svc = ListItemService(items, lists, reg, notification_service=notif)
    item = await svc.create(CID, lst.id, lst.owner_id, {"due": "Buy milk"})
    notif.notify.assert_awaited_once()
    args, kwargs = notif.notify.await_args
    assert args[0] == member
    assert args[1] == "list_item"
    assert {"list_id", "item_id", "item_title", "adder_id"} <= set(args[2])
    assert args[2]["item_id"] == str(item.id)
    assert args[2]["item_title"] == "Buy milk"
    assert args[2]["adder_id"] == str(lst.owner_id)
    assert kwargs["actor_id"] == lst.owner_id


async def test_create_without_notifier_does_not_fail(svc, lst):
    s, _, lists, _ = svc
    await s.create(CID, lst.id, lst.owner_id, {})
    lists.audience_ids.assert_not_called()
