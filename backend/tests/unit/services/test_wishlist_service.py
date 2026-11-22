"""
@file test_wishlist_service.py
@brief Wishlists v2: claim visibility (surprise vs open lists), gift and fund
       claims, per-giver cap, recipients, validation.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError as PydanticError

from app.core.exceptions import AuthorizationError, NotFoundError, ValidationError
from app.repositories.wishlist_item_repo import WishlistItemRepository
from app.repositories.wishlist_repo import WishlistRepository
from app.schemas.wishlist import ClaimIn, ItemIn, RecipientIn, WishlistCreate
from app.services.wishlist_gift_service import WishlistGiftService
from app.services.wishlist_service import WishlistService

CID = uuid.uuid4()
OWNER = SimpleNamespace(id=uuid.uuid4(), display_name="Ruth", role="member")
AUNT = SimpleNamespace(id=uuid.uuid4(), display_name="Maya", role="member")


def _list(**kw):
    base = dict(
        id=uuid.uuid4(),
        owner_id=OWNER.id,
        community_id=CID,
        title="Biscuit turns 5",
        occasion="birthday",
        occasion_label=None,
        event_date=None,
        due_by=None,
        note=None,
        visibility="groups",
        currency="USD",
        budget_min_cents=None,
        budget_max_cents=None,
        event_budget_cents=None,
        giver_cap_cents=None,
        hide_claims=True,
        registry_links=[],
    )
    return SimpleNamespace(**{**base, **kw})


def _item(**kw):
    base = dict(
        id=uuid.uuid4(),
        kind="gift",
        name="Squeaky duck",
        url=None,
        price_cents=800,
        goal_cents=None,
        notes=None,
        qty=2,
        preview_id=None,
    )
    return SimpleNamespace(**{**base, **kw})


def _claim(item, user, qty=1, amount=None):
    return (
        SimpleNamespace(item_id=item.id, user_id=user.id, qty=qty, amount_cents=amount),
        user.display_name,
    )


def _svcs(w, items, claims=(), recipient=False):
    repo = AsyncMock(spec=WishlistRepository)
    repo.get_visible.return_value = w
    repo.recipients.return_value = []
    repo.user_names.return_value = {OWNER.id: "Ruth"}
    repo.household_names.return_value = {}
    repo.group_names.return_value = {}
    repo.is_recipient.return_value = recipient
    irepo = AsyncMock(spec=WishlistItemRepository)
    irepo.items.return_value = items
    irepo.item.side_effect = lambda _w, iid, lock=False: next(
        (i for i in items if i.id == iid), None
    )
    irepo.claims.return_value = list(claims)
    irepo.previews.return_value = {}
    lists = WishlistService(repo, irepo, CID)
    return lists, WishlistGiftService(lists, irepo, CID), repo, irepo


async def test_owner_never_sees_claims_on_surprise_list() -> None:
    w, it = _list(), _item()
    lists, *_ = _svcs(w, [it], [_claim(it, AUNT)])
    d = await lists.get(w.id, OWNER)  # type: ignore[arg-type]
    assert d.is_owner and not d.sees_claims
    assert d.items[0].claimed is None and d.items[0].claimers is None
    assert d.planned_cents == 1600


async def test_open_list_shows_claimers_to_everyone() -> None:
    w, it = _list(hide_claims=False, occasion="reunion"), _item()
    lists, *_ = _svcs(w, [it], [_claim(it, AUNT)])
    d = await lists.get(w.id, OWNER)  # type: ignore[arg-type]
    assert d.sees_claims and d.items[0].claimers[0].name == "Maya"


async def test_giver_sees_totals_and_own_spend() -> None:
    w, it = _list(), _item()
    lists, *_ = _svcs(w, [it], [_claim(it, AUNT)])
    d = await lists.get(w.id, AUNT)  # type: ignore[arg-type]
    assert (d.items[0].claimed, d.items[0].mine, d.my_total_cents) == (1, 1, 800)
    assert d.planned_cents is None


async def test_gift_claim_respects_what_is_left() -> None:
    w, it = _list(), _item(qty=2)
    other = SimpleNamespace(id=uuid.uuid4(), display_name="Leo")
    _, gifts, _, irepo = _svcs(w, [it], [_claim(it, other)])
    with pytest.raises(ValidationError):
        await gifts.claim(w.id, it.id, ClaimIn(qty=2), AUNT)  # type: ignore[arg-type]
    await gifts.claim(w.id, it.id, ClaimIn(qty=1), AUNT)  # type: ignore[arg-type]
    irepo.set_claim.assert_awaited_once_with(it, AUNT.id, 1, None, CID)


async def test_fund_pledge_capped_at_goal_and_needs_amount() -> None:
    w, fund = _list(), _item(kind="fund", goal_cents=50_000, price_cents=None, qty=1)
    _, gifts, _, irepo = _svcs(w, [fund], [_claim(fund, OWNER, amount=45_000)])
    with pytest.raises(ValidationError):
        await gifts.claim(w.id, fund.id, ClaimIn(), AUNT)  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        await gifts.claim(w.id, fund.id, ClaimIn(amount_cents=6_000), AUNT)  # type: ignore[arg-type]
    await gifts.claim(w.id, fund.id, ClaimIn(amount_cents=5_000), AUNT)  # type: ignore[arg-type]
    irepo.set_claim.assert_awaited_once_with(fund, AUNT.id, 1, 5_000, CID)


async def test_per_giver_cap() -> None:
    w = _list(giver_cap_cents=2_000)
    duck, bed = _item(price_cents=800, qty=3), _item(price_cents=1_500, qty=1)
    _, gifts, _, irepo = _svcs(w, [duck, bed], [_claim(duck, AUNT, qty=1)])
    with pytest.raises(ValidationError):
        await gifts.claim(w.id, bed.id, ClaimIn(), AUNT)  # type: ignore[arg-type]
    await gifts.claim(w.id, duck.id, ClaimIn(qty=2), AUNT)  # replaces own claim: 1600 <= 2000
    irepo.set_claim.assert_awaited_once()


async def test_people_on_a_surprise_list_cannot_claim() -> None:
    w, it = _list(), _item()
    _, gifts, _, irepo = _svcs(w, [it], recipient=True)
    with pytest.raises(ValidationError):
        await gifts.claim(w.id, it.id, ClaimIn(), AUNT)  # type: ignore[arg-type]
    irepo.set_claim.assert_not_awaited()


async def test_member_recipient_edits_items_but_not_settings() -> None:
    w = _list()
    lists, gifts, _, irepo = _svcs(w, [], recipient=True)
    await gifts.add_item(w.id, ItemIn(name="Ball"), AUNT)  # type: ignore[arg-type]
    irepo.add.assert_awaited_once()
    with pytest.raises(AuthorizationError):
        await lists.delete(w.id, AUNT)  # type: ignore[arg-type]


async def test_strangers_cannot_add_items() -> None:
    w = _list()
    _, gifts, _, irepo = _svcs(w, [])
    with pytest.raises(AuthorizationError):
        await gifts.add_item(w.id, ItemIn(name="Ball"), AUNT)  # type: ignore[arg-type]


async def test_hidden_list_is_not_found() -> None:
    lists, *_ = _svcs(None, [])
    with pytest.raises(NotFoundError):
        await lists.get(uuid.uuid4(), AUNT)  # type: ignore[arg-type]


async def test_recipients_validated_and_everyone_wins() -> None:
    w = _list()
    lists, _, repo, _ = _svcs(w, [])
    repo.visible.return_value = []
    repo.create.return_value = w
    repo.my_group_ids.return_value = set()
    with pytest.raises(NotFoundError):
        await lists.create(
            WishlistCreate(
                title="BBQ", recipients=[RecipientIn(kind="subgroup", ref_id=uuid.uuid4())]
            ),
            OWNER,  # type: ignore[arg-type]
        )
    await lists.create(
        WishlistCreate(
            title="Reunion",
            recipients=[RecipientIn(kind="name", name="Grandpa Joe"), RecipientIn(kind="everyone")],
        ),
        OWNER,  # type: ignore[arg-type]
    )
    assert repo.replace_recipients.await_args.args[1] == [{"kind": "everyone"}]
    assert repo.create.await_args.kwargs["visibility"] == "community"


async def test_update_keeps_everyone_lists_public() -> None:
    w = _list()
    lists, _, repo, _ = _svcs(w, [])
    repo.recipients.return_value = [
        SimpleNamespace(kind="everyone", ref_id=None, name=None, wishlist_id=w.id)
    ]
    from app.schemas.wishlist import WishlistUpdate

    await lists.update(w.id, WishlistUpdate(visibility="private"), OWNER)  # type: ignore[arg-type]
    assert repo.update.await_args.args[1]["visibility"] == "community"


async def test_default_recipient_is_creator() -> None:
    w = _list()
    lists, _, repo, _ = _svcs(w, [])
    repo.visible.return_value = []
    repo.create.return_value = w
    repo.user_names.return_value = {OWNER.id: "Ruth"}
    await lists.create(WishlistCreate(title="Mine"), OWNER)  # type: ignore[arg-type]
    assert repo.replace_recipients.await_args.args[1] == [
        {"kind": "user", "ref_id": OWNER.id, "name": None}
    ]


def test_validation_rules() -> None:
    with pytest.raises(PydanticError):
        ItemIn(name="x", url="javascript:alert(1)")
    with pytest.raises(PydanticError):
        ItemIn(name="Honeymoon", kind="fund")
    assert ItemIn(name="Fund", kind="fund", goal_cents=500, qty=3, price_cents=9).qty == 1
    with pytest.raises(PydanticError):
        WishlistCreate(title="x", budget_min_cents=500, budget_max_cents=100)
    import datetime as dt

    with pytest.raises(PydanticError):
        WishlistCreate(title="x", event_date=dt.date(2026, 12, 1), due_by=dt.date(2026, 12, 5))
    with pytest.raises(PydanticError):
        RecipientIn(kind="name", name="  ")
