"""@file Activity-log recording from the item, completion and signup services."""

import uuid
from unittest.mock import AsyncMock, MagicMock

from app.models.list import List, ListItem, ListItemSignup
from app.repositories.list_completion_repo import ListCompletionRepository
from app.repositories.list_item_repo import ListItemRepository
from app.repositories.list_repo import ListRepository
from app.repositories.list_signup_repo import ListSignupRepository
from app.services.list_completion_service import ListCompletionService
from app.services.list_field_registry import ListFieldRegistry
from app.services.list_items_service import ListItemService
from app.services.list_signup_service import ListSignupService

CID = uuid.uuid4()
USER = uuid.uuid4()


def _fixtures():
    lst = MagicMock(spec=List)
    lst.id, lst.owner_id, lst.title, lst.visibility = uuid.uuid4(), USER, "L", "community"
    lst.field_schema = [{"key": "title", "type_key": "text", "config": {}}]
    item = MagicMock(spec=ListItem)
    item.id, item.list_id, item.completed = uuid.uuid4(), lst.id, False
    item.values, item.signup_quantity_needed = {"title": "Chairs"}, 2
    lists = AsyncMock(spec=ListRepository)
    lists.get_by_id.return_value = lst
    lists.can_view.return_value = True
    items = AsyncMock(spec=ListItemRepository)
    items.get_by_id.return_value = item
    items.create.side_effect = lambda e: e
    items.update.side_effect = lambda e, d: e
    items.lock_item_for_update.return_value = item
    return lst, item, lists, items, AsyncMock()


def _items_svc(activity):
    lst, item, lists, items, _ = _fixtures()
    reg = MagicMock(spec=ListFieldRegistry)
    reg.validate_value.side_effect = lambda k, v, c: v
    reg.project_columns.return_value = {}
    return ListItemService(items, lists, reg, activity=activity), lst, item


async def test_item_add_edit_remove_are_logged():
    act = AsyncMock()
    svc, lst, item = _items_svc(act)
    await svc.create(CID, lst.id, USER, {"title": "Chairs"})
    await svc.update(CID, item.id, USER, {"title": "Chairs"})
    await svc.delete(CID, item.id, USER)
    assert [c.args[2] for c in act.record.await_args_list] == [
        "item_added",
        "item_edited",
        "item_removed",
    ]
    assert act.record.await_args_list[2].args[4] == "Chairs"


async def test_item_service_works_without_recorder():
    svc, lst, _ = _items_svc(None)
    await svc.create(CID, lst.id, USER, {"title": "x"})


async def test_complete_and_uncomplete_are_logged():
    lst, item, lists, items, act = _fixtures()
    lst.field_schema = [{"key": "done", "type": "checkbox", "config": {}}]
    svc = ListCompletionService(
        items,
        lists,
        AsyncMock(spec=ListCompletionRepository),
        ListFieldRegistry(),
        AsyncMock(),
        AsyncMock(),
        CID,
        act,
    )
    await svc.complete_item(item.id, USER)
    item.completed = True
    await svc.uncomplete_item(item.id, USER)
    assert [c.args[2] for c in act.record.await_args_list] == ["completed", "uncompleted"]


async def test_signup_claim_and_release_are_logged():
    lst, item, lists, items, act = _fixtures()
    signups = AsyncMock(spec=ListSignupRepository)
    claim = MagicMock(spec=ListItemSignup)
    claim.user_id, claim.quantity = USER, 1
    signups.list_for_item.side_effect = [[], [claim]]
    signups.create_claim.return_value = claim
    svc = ListSignupService(items, signups, lists, MagicMock(), AsyncMock(), AsyncMock(), act)
    session = AsyncMock()
    session.get.return_value = None
    await svc.claim_signup(item.id, USER, 1, session)
    await svc.release_signup(item.id, USER, session)
    assert [c.args[2] for c in act.record.await_args_list] == [
        "signup_claimed",
        "signup_released",
    ]
