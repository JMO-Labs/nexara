"""
@file wishlist_ship.py
@brief Wishlist shipping address: free text, a person's profile address,
       or an event's location (both used live). An event shows only to
       viewers who can see that event. A person's address may only be used when it is theirs (the
       list creator's) or they share it with the whole community, the same
       rule lists use for pulled contact fields.
"""

from __future__ import annotations

import uuid

from app.core.exceptions import ValidationError
from app.core.i18n import _
from app.models.user import User
from app.models.user_settings import UserSettings
from app.models.wishlist import Wishlist
from app.repositories.wishlist_repo import WishlistRepository
from app.schemas.wishlist import ShipTo
from app.services.profiles.visibility import effective_levels


def shares_address(user: User, prefs: UserSettings | None, creator_id: uuid.UUID) -> bool:
    """@brief The creator's own address, or one shared with the community."""
    if user.id == creator_id:
        return True
    levels = effective_levels(
        prefs.field_visibility if prefs else None,
        prefs.profile_visible_to if prefs else "community",
    )
    return levels["address"] == "community"


async def check_ship_user(
    repo: WishlistRepository, user_id: uuid.UUID, creator_id: uuid.UUID, cid: uuid.UUID
) -> None:
    """@throws ValidationError when that person's address can't be used."""
    row = await repo.ship_user(user_id, cid)
    if row is None or not shares_address(row[0], row[1], creator_id):
        raise ValidationError(
            message=_("That person doesn't share their address. Ask them to share it.")
        )


async def check_ship_event(
    repo: WishlistRepository, event_id: uuid.UUID, creator_id: uuid.UUID, cid: uuid.UUID
) -> None:
    """@throws ValidationError unless the creator can see that event."""
    if await repo.ship_event(event_id, cid, creator_id) is None:
        raise ValidationError(message=_("Event not found"))


async def ship_to(
    repo: WishlistRepository, w: Wishlist, cid: uuid.UUID, viewer_id: uuid.UUID
) -> ShipTo | None:
    """@brief The list's shipping address as this viewer may see it."""
    if w.ship_to_text:
        return ShipTo(address=w.ship_to_text)
    if w.ship_to_event_id:
        ev = await repo.ship_event(w.ship_to_event_id, cid, viewer_id)
        if ev is None:  # viewer can't see the event: don't reveal where it is
            return ShipTo(name="the event")
        return ShipTo(
            event_id=ev.id, name=ev.title, address=ev.location or None, starts_at=ev.starts_at
        )
    if not w.ship_to_user_id:
        return None
    row = await repo.ship_user(w.ship_to_user_id, cid)
    if row is None:
        return None
    user, prefs = row
    shared = shares_address(user, prefs, w.owner_id)  # re-checked: they may stop sharing
    return ShipTo(
        user_id=user.id,
        name=user.display_name,
        address=(user.address or None) if shared else None,
    )
