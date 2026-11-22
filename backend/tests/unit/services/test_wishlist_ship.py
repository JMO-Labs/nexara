"""@file test_wishlist_ship.py @brief Ship-to: sharing rule enforced, re-checked live."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import ValidationError
from app.schemas.wishlist import WishlistUpdate
from app.services.wishlist_ship import check_ship_event, check_ship_user, ship_to

CID, CREATOR, VIEWER = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()


def _person(level: str | None, uid: uuid.UUID | None = None):
    user = SimpleNamespace(id=uid or uuid.uuid4(), display_name="Grandma", address="1 Elm St")
    prefs = SimpleNamespace(
        field_visibility={"address": level} if level else {}, profile_visible_to="community"
    )
    return user, prefs


def _list(**kw):
    return SimpleNamespace(
        **{
            "owner_id": CREATOR,
            "ship_to_text": None,
            "ship_to_user_id": None,
            "ship_to_event_id": None,
            **kw,
        }
    )


async def test_only_shared_or_own_address_can_be_used():
    repo = AsyncMock()
    repo.ship_user.return_value = _person("community")
    await check_ship_user(repo, uuid.uuid4(), CREATOR, CID)
    for level in ("groups", "private", None):  # new fields default to private
        repo.ship_user.return_value = _person(level)
        with pytest.raises(ValidationError):
            await check_ship_user(repo, uuid.uuid4(), CREATOR, CID)
    repo.ship_user.return_value = _person("private", CREATOR)  # your own address
    await check_ship_user(repo, CREATOR, CREATOR, CID)
    repo.ship_user.return_value = None  # not in this community
    with pytest.raises(ValidationError):
        await check_ship_user(repo, uuid.uuid4(), CREATOR, CID)


async def test_live_address_hidden_after_they_stop_sharing():
    repo = AsyncMock()
    user, prefs = _person("community")
    repo.ship_user.return_value = (user, prefs)
    w = _list(ship_to_user_id=user.id)
    assert (await ship_to(repo, w, CID, VIEWER)).address == "1 Elm St"
    repo.ship_user.assert_awaited_with(user.id, CID, VIEWER)  # block filter is per viewer
    prefs.field_visibility = {"address": "private"}
    out = await ship_to(repo, w, CID, VIEWER)
    assert out.name == "Grandma" and out.address is None
    repo.ship_user.return_value = None  # blocked either way
    blocked = await ship_to(repo, w, CID, VIEWER)
    assert blocked.address is None and blocked.user_id is None and blocked.name != "Grandma"
    assert (await ship_to(repo, _list(ship_to_text="PO Box 9"), CID, VIEWER)).address == "PO Box 9"
    assert await ship_to(repo, _list(), CID, VIEWER) is None


async def test_event_location_only_for_viewers_who_see_the_event():
    from datetime import UTC, datetime

    ev = SimpleNamespace(
        id=uuid.uuid4(), title="Family BBQ", location="Lake Park", starts_at=datetime.now(UTC)
    )
    repo = AsyncMock()
    repo.ship_event.return_value = ev
    w = _list(ship_to_event_id=ev.id)
    out = await ship_to(repo, w, CID, VIEWER)
    assert (out.name, out.address, out.event_id) == ("Family BBQ", "Lake Park", ev.id)
    repo.ship_event.assert_awaited_with(ev.id, CID, VIEWER)
    repo.ship_event.return_value = None  # private/subgroup event this viewer can't see
    hidden = await ship_to(repo, w, CID, VIEWER)
    assert hidden.address is None and hidden.event_id is None and hidden.name == "the event"
    with pytest.raises(ValidationError):
        await check_ship_event(repo, ev.id, CREATOR, CID)


def test_text_and_person_are_exclusive():
    with pytest.raises(ValueError):
        WishlistUpdate(ship_to_text="x", ship_to_user_id=uuid.uuid4())
    with pytest.raises(ValueError):
        WishlistUpdate(ship_to_user_id=uuid.uuid4(), ship_to_event_id=uuid.uuid4())
    assert WishlistUpdate(ship_to_text="  ").ship_to_text is None
