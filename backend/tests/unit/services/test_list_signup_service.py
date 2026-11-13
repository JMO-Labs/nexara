"""@file Tests for ListSignupService (claims, release, race safety)."""

import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import AppError, NotFoundError
from app.models.list import List, ListItem, ListItemSignup
from app.repositories.list_item_repo import ListItemRepository
from app.repositories.list_repo import ListRepository
from app.repositories.list_signup_repo import ListSignupRepository
from app.services.list_signup_service import ListSignupService


def _build(needed=1, claims=None):
    item = MagicMock(spec=ListItem)
    item.id, item.list_id, item.signup_quantity_needed = uuid.uuid4(), uuid.uuid4(), needed
    lst = MagicMock(spec=List)
    lst.id, lst.owner_id, lst.community_id = item.list_id, uuid.uuid4(), uuid.uuid4()
    store: list = list(claims or [])
    lock = asyncio.Lock()
    held = {"locked": False}

    item_repo = AsyncMock(spec=ListItemRepository)
    signup_repo = AsyncMock(spec=ListSignupRepository)
    list_repo = AsyncMock(spec=ListRepository)
    list_repo.get_by_id.return_value = lst

    async def lock_item(item_id, session=None):
        if item_id != item.id:
            return None
        await lock.acquire()
        held["locked"] = True
        return item

    async def create_claim(item_id, user_id, quantity=1, note=None):
        await asyncio.sleep(0)  # yield: would expose a race without the lock
        c = MagicMock(spec=ListItemSignup)
        c.item_id, c.user_id, c.quantity = item_id, user_id, quantity
        store.append(c)
        return c

    async def delete_claim(item_id, user_id):
        for c in store:
            if c.user_id == user_id:
                store.remove(c)
                return True
        return False

    item_repo.lock_item_for_update.side_effect = lock_item
    signup_repo.create_claim.side_effect = create_claim
    signup_repo.delete_claim.side_effect = delete_claim
    signup_repo.list_for_item.side_effect = lambda _i: list(store)
    session = AsyncMock()
    # release the fake row lock on "commit"
    session.flush.side_effect = lambda: None
    bus, notif = AsyncMock(), AsyncMock()
    svc = ListSignupService(item_repo, signup_repo, list_repo, MagicMock(), bus, notif)
    svc._release_lock = lambda: lock.release() if lock.locked() else None
    return svc, item, lst, item_repo, signup_repo, list_repo, bus, notif, session, store


async def test_claim_uses_row_lock_and_decrements():
    svc, item, lst, item_repo, signup_repo, list_repo, bus, notif, session, _ = _build(3)
    uid = uuid.uuid4()
    await svc.claim_signup(item.id, uid, 2, session)
    item_repo.lock_item_for_update.assert_awaited_once_with(item.id, session)
    assert item.signup_quantity_needed == 1
    list_repo.increment_counters.assert_awaited_once_with(lst.id, {"signup_count": 1})
    bus.emit.assert_awaited_once()
    notif.notify.assert_awaited_once()


async def test_claim_exceeding_needed_raises():
    svc, item, *_, session, _ = _build(1)
    with pytest.raises(AppError) as exc:
        await svc.claim_signup(item.id, uuid.uuid4(), 2, session)
    assert exc.value.status_code == 409


async def test_claim_when_no_slots_raises():
    svc, item, *_, session, _ = _build(0)
    with pytest.raises(AppError):
        await svc.claim_signup(item.id, uuid.uuid4(), 1, session)


async def test_claim_twice_by_same_user_raises():
    svc, item, *_, session, _ = _build(5)
    uid = uuid.uuid4()
    await svc.claim_signup(item.id, uid, 1, session)
    svc._release_lock()
    with pytest.raises(AppError):
        await svc.claim_signup(item.id, uid, 1, session)


async def test_claim_invalid_quantity_and_missing_item():
    svc, item, *_, session, _ = _build(2)
    with pytest.raises(AppError):
        await svc.claim_signup(item.id, uuid.uuid4(), 0, session)
    with pytest.raises(NotFoundError):
        await svc.claim_signup(uuid.uuid4(), uuid.uuid4(), 1, session)


async def test_release_restores_quantity_and_counter():
    svc, item, lst, _, _, list_repo, bus, _, session, _ = _build(3)
    uid = uuid.uuid4()
    await svc.claim_signup(item.id, uid, 2, session)
    svc._release_lock()
    list_repo.increment_counters.reset_mock()
    await svc.release_signup(item.id, uid, session)
    assert item.signup_quantity_needed == 3
    list_repo.increment_counters.assert_awaited_once_with(lst.id, {"signup_count": -1})
    assert bus.emit.await_count == 2


async def test_release_without_claim_raises():
    svc, item, *_, session, _ = _build(3)
    with pytest.raises(NotFoundError):
        await svc.release_signup(item.id, uuid.uuid4(), session)


async def test_queries():
    svc, item, _, _, signup_repo, *_ = _build(3)
    uid = uuid.uuid4()
    session = AsyncMock()
    await svc.claim_signup(item.id, uid, 1, session)
    assert len(await svc.get_signups_for_item(item.id)) == 1
    assert (await svc.get_signup(item.id, uid)).user_id == uid
    assert await svc.get_signup(item.id, uuid.uuid4()) is None


async def test_race_two_concurrent_claims_one_wins():
    svc, item, *_, session, store = _build(1)

    async def attempt(uid):
        try:
            return await svc.claim_signup(item.id, uid, 1, session)
        finally:
            svc._release_lock()  # simulate transaction end

    results = await asyncio.gather(
        attempt(uuid.uuid4()), attempt(uuid.uuid4()), return_exceptions=True
    )
    ok = [r for r in results if not isinstance(r, Exception)]
    bad = [r for r in results if isinstance(r, AppError)]
    assert len(ok) == 1 and len(bad) == 1
    assert len(store) == 1
    assert item.signup_quantity_needed == 0
