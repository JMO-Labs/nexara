"""
@file test_wishlist_service.py
@brief Wishlists: owners never see claims, claim limits, owner-only edits,
       household lists only for members you manage.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import AuthorizationError, NotFoundError, ValidationError
from app.repositories.wishlist_repo import WishlistRepository
from app.schemas.wishlist import ItemIn, WishlistCreate
from app.services.wishlist_service import WishlistService

CID = uuid.uuid4()
OWNER = SimpleNamespace(id=uuid.uuid4(), display_name="Ruth")
AUNT = SimpleNamespace(id=uuid.uuid4(), display_name="Maya")


def _list(household_id=None):
    return SimpleNamespace(
        id=uuid.uuid4(),
        owner_id=OWNER.id,
        household_id=household_id,
        title="Biscuit's birthday",
        occasion="birthday",
        occasion_date=None,
        note=None,
        visibility="groups",
    )


def _item(qty=2):
    return SimpleNamespace(
        id=uuid.uuid4(), name="Squeaky duck", url=None, price="$8", notes=None, qty=qty
    )


def _svc(w, items, totals=None):
    repo = AsyncMock(spec=WishlistRepository)
    repo.get_visible.return_value = w
    repo.items.return_value = items
    repo.claim_totals.return_value = totals or {}
    repo.household_names.return_value = {}
    repo.item.return_value = items[0] if items else None
    return WishlistService(repo, CID), repo


async def test_owner_never_sees_claims() -> None:
    w, it = _list(), _item()
    svc, repo = _svc(w, [it], {it.id: (2, 0)})
    detail = await svc.get(w.id, OWNER)  # type: ignore[arg-type]
    assert detail.is_owner and detail.items[0].claimed is None and detail.items[0].mine is None
    repo.claim_totals.assert_not_awaited()


async def test_others_see_claim_totals_and_their_own() -> None:
    w, it = _list(), _item()
    svc, _ = _svc(w, [it], {it.id: (2, 1)})
    detail = await svc.get(w.id, AUNT)  # type: ignore[arg-type]
    assert not detail.is_owner
    assert (detail.items[0].claimed, detail.items[0].mine) == (2, 1)


async def test_claim_respects_what_is_left() -> None:
    w, it = _list(), _item(qty=2)
    svc, repo = _svc(w, [it], {it.id: (1, 0)})
    with pytest.raises(ValidationError):
        await svc.claim(w.id, it.id, 2, AUNT)  # type: ignore[arg-type]
    await svc.claim(w.id, it.id, 1, AUNT)  # type: ignore[arg-type]
    repo.set_claim.assert_awaited_once_with(it, AUNT.id, 1, CID)
    assert repo.item.await_args.kwargs == {"lock": True}


async def test_raising_your_own_claim_counts_only_others() -> None:
    w, it = _list(), _item(qty=2)
    svc, repo = _svc(w, [it], {it.id: (1, 1)})
    await svc.claim(w.id, it.id, 2, AUNT)  # type: ignore[arg-type]
    repo.set_claim.assert_awaited_once()


async def test_owner_cannot_claim_own_list() -> None:
    w, it = _list(), _item()
    svc, repo = _svc(w, [it])
    with pytest.raises(ValidationError):
        await svc.claim(w.id, it.id, 1, OWNER)  # type: ignore[arg-type]
    repo.set_claim.assert_not_awaited()


async def test_only_owner_edits() -> None:
    w = _list()
    svc, repo = _svc(w, [])
    with pytest.raises(AuthorizationError):
        await svc.add_item(w.id, ItemIn(name="Ball"), AUNT)  # type: ignore[arg-type]
    repo.add_item.assert_not_awaited()


async def test_hidden_list_is_not_found() -> None:
    svc, repo = _svc(None, [])
    with pytest.raises(NotFoundError):
        await svc.get(uuid.uuid4(), AUNT)  # type: ignore[arg-type]


async def test_household_list_needs_a_member_you_manage() -> None:
    svc, repo = _svc(_list(), [])
    repo.owned_household.return_value = None
    with pytest.raises(NotFoundError):
        await svc.create(
            WishlistCreate(title="Toys", household_id=uuid.uuid4()),
            AUNT,  # type: ignore[arg-type]
        )
    repo.create.assert_not_awaited()


def test_item_links_must_be_http() -> None:
    from pydantic import ValidationError as PydanticError

    with pytest.raises(PydanticError):
        ItemIn(name="x", url="javascript:alert(1)")
    assert ItemIn(name="x", url="  ", price=" ").url is None
