"""
@file test_list_item_claims.py
@brief Unit tests for ListItemService add/complete/claim/release.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import AppError, NotFoundError
from app.models.list import List, ListItem
from app.repositories.list_item_repo import ListItemRepository
from app.repositories.list_repo import ListRepository
from app.repositories.list_signup_repo import ListSignupRepository
from app.services.list_item_service import ListItemService

CID = uuid.UUID("00000000-0000-0000-0000-000000000001")
UID = uuid.uuid4()


def _item(needed=None, completed=False) -> MagicMock:
    obj = MagicMock(spec=ListItem)
    obj.id = uuid.uuid4()
    obj.list_id = uuid.uuid4()
    obj.signup_quantity_needed = needed
    obj.completed = completed
    return obj


def _svc():
    lists = AsyncMock(spec=ListRepository)
    items = AsyncMock(spec=ListItemRepository)
    signups = AsyncMock(spec=ListSignupRepository)
    lst = MagicMock(spec=List)
    lst.id = uuid.uuid4()
    lists.get_by_id.return_value = lst
    items.create.side_effect = lambda e: e
    svc = ListItemService(lists, items, signups, CID, AsyncMock())
    return svc, lists, items, signups, lst


class TestAddItem:
    async def test_creates_and_increments(self):
        svc, lists, items, _, lst = _svc()
        item = await svc.add_item(lst.id, {"title": "x"}, quantity_needed=3)
        assert item.signup_quantity_needed == 3
        lists.increment_counters.assert_awaited_once_with(lst.id, {"item_count": 1})

    async def test_missing_list(self):
        svc, lists, *_ = _svc()
        lists.get_by_id.return_value = None
        with pytest.raises(NotFoundError):
            await svc.add_item(uuid.uuid4(), {})


class TestComplete:
    async def test_complete_increments(self):
        svc, lists, items, _, _ = _svc()
        item = _item()
        items.get_by_id.return_value = item
        await svc.complete(item.id)
        assert item.completed is True
        lists.increment_counters.assert_awaited_once_with(item.list_id, {"completed_count": 1})

    async def test_complete_idempotent(self):
        svc, lists, items, _, _ = _svc()
        items.get_by_id.return_value = _item(completed=True)
        await svc.complete(uuid.uuid4())
        lists.increment_counters.assert_not_awaited()

    async def test_uncomplete_decrements(self):
        svc, lists, items, _, _ = _svc()
        item = _item(completed=True)
        items.get_by_id.return_value = item
        await svc.uncomplete(item.id)
        assert item.completed is False
        lists.increment_counters.assert_awaited_once_with(item.list_id, {"completed_count": -1})

    async def test_uncomplete_noop_when_open(self):
        svc, lists, items, _, _ = _svc()
        items.get_by_id.return_value = _item()
        await svc.uncomplete(uuid.uuid4())
        lists.increment_counters.assert_not_awaited()

    async def test_not_found(self):
        svc, _, items, _, _ = _svc()
        items.get_by_id.return_value = None
        with pytest.raises(NotFoundError):
            await svc.complete(uuid.uuid4())


class TestClaim:
    async def test_claim_creates_signup(self):
        svc, lists, items, signups, _ = _svc()
        item = _item(needed=2)
        items.lock_item_for_update.return_value = item
        signups.sum_claimed.return_value = 1
        await svc.claim(item.id, UID)
        signups.create_claim.assert_awaited_once_with(item.id, UID, 1, None)
        lists.increment_counters.assert_awaited_once_with(item.list_id, {"signup_count": 1})

    async def test_claim_unlimited(self):
        svc, _, items, signups, _ = _svc()
        items.lock_item_for_update.return_value = _item(needed=None)
        await svc.claim(uuid.uuid4(), UID, quantity=5)
        signups.create_claim.assert_awaited_once()
        signups.sum_claimed.assert_not_awaited()

    async def test_claim_full_raises_no_slots(self):
        svc, lists, items, signups, _ = _svc()
        items.lock_item_for_update.return_value = _item(needed=2)
        signups.sum_claimed.return_value = 2
        with pytest.raises(AppError, match="no slots"):
            await svc.claim(uuid.uuid4(), UID)
        signups.create_claim.assert_not_awaited()
        lists.increment_counters.assert_not_awaited()

    async def test_claim_exceeding_remaining(self):
        svc, _, items, signups, _ = _svc()
        items.lock_item_for_update.return_value = _item(needed=3)
        signups.sum_claimed.return_value = 2
        with pytest.raises(AppError, match="no slots"):
            await svc.claim(uuid.uuid4(), UID, quantity=2)

    async def test_claim_bad_quantity(self):
        svc, *_ = _svc()
        with pytest.raises(AppError):
            await svc.claim(uuid.uuid4(), UID, quantity=0)

    async def test_claim_item_missing(self):
        svc, _, items, _, _ = _svc()
        items.lock_item_for_update.return_value = None
        with pytest.raises(NotFoundError):
            await svc.claim(uuid.uuid4(), UID)


class TestRelease:
    async def test_release_decrements(self):
        svc, lists, items, signups, _ = _svc()
        item = _item()
        items.lock_item_for_update.return_value = item
        signups.delete_claim.return_value = True
        await svc.release(item.id, UID)
        lists.increment_counters.assert_awaited_once_with(item.list_id, {"signup_count": -1})

    async def test_release_without_claim(self):
        svc, lists, items, signups, _ = _svc()
        items.lock_item_for_update.return_value = _item()
        signups.delete_claim.return_value = False
        with pytest.raises(NotFoundError):
            await svc.release(uuid.uuid4(), UID)
        lists.increment_counters.assert_not_awaited()


class TestTenantIsolation:
    """Items whose parent list is outside the community must look missing."""

    async def test_complete_foreign_list(self):
        svc, lists, items, signups, _ = _svc()
        item = _item()
        items.get_by_id.return_value = item
        lists.get_by_id.return_value = None
        with pytest.raises(NotFoundError):
            await svc.complete(item.id)
        assert item.completed is False
        lists.increment_counters.assert_not_awaited()

    async def test_claim_foreign_list(self):
        svc, lists, items, signups, _ = _svc()
        items.lock_item_for_update.return_value = _item()
        lists.get_by_id.return_value = None
        with pytest.raises(NotFoundError):
            await svc.claim(uuid.uuid4(), UID)
        signups.create_claim.assert_not_awaited()
        lists.increment_counters.assert_not_awaited()

    async def test_release_foreign_list(self):
        svc, lists, items, signups, _ = _svc()
        items.lock_item_for_update.return_value = _item()
        lists.get_by_id.return_value = None
        with pytest.raises(NotFoundError):
            await svc.release(uuid.uuid4(), UID)
        signups.delete_claim.assert_not_awaited()
        lists.increment_counters.assert_not_awaited()
