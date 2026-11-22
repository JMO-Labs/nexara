"""
@file wishlist_service.py
@brief Wishlists: owners (or the parent managing a household member/pet)
       edit lists and items; everyone else who can see a list claims items.
       Owners never see claims, so gifts stay a surprise.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.core.exceptions import AuthorizationError, NotFoundError, ValidationError
from app.core.i18n import _
from app.models.user import User
from app.models.wishlist import Wishlist, WishlistItem
from app.repositories.wishlist_repo import WishlistRepository
from app.schemas.wishlist import (
    HouseholdBrief,
    ItemIn,
    ItemOut,
    ItemUpdate,
    WishlistCreate,
    WishlistDetail,
    WishlistOut,
    WishlistUpdate,
)

MAX_LISTS = 50
MAX_ITEMS = 100


class WishlistService:
    """@brief Wishlist rules, scoped to one community."""

    def __init__(self, repo: WishlistRepository, community_id: uuid.UUID) -> None:
        self._repo = repo
        self._cid = community_id

    async def _summaries(self, rows: list[tuple[Wishlist, int]], viewer: User) -> list[WishlistOut]:
        names = await self._repo.household_names(
            [w.household_id for w, _n in rows if w.household_id]
        )
        out = []
        for w, n in rows:
            hh = names.get(w.household_id) if w.household_id else None
            out.append(
                WishlistOut(
                    id=w.id,
                    owner_id=w.owner_id,
                    title=w.title,
                    occasion=w.occasion,
                    occasion_date=w.occasion_date,
                    note=w.note,
                    visibility=w.visibility,
                    household=HouseholdBrief(id=w.household_id, name=hh[0], kind=hh[1])
                    if hh and w.household_id
                    else None,
                    item_count=n,
                    is_owner=w.owner_id == viewer.id,
                )
            )
        return out

    async def _visible(self, wishlist_id: uuid.UUID, viewer: User) -> Wishlist:
        row = await self._repo.get_visible(wishlist_id, viewer.id, self._cid)
        if row is None:
            raise NotFoundError(message=_("Wishlist not found"))
        return row

    async def _owned(self, wishlist_id: uuid.UUID, viewer: User) -> Wishlist:
        row = await self._visible(wishlist_id, viewer)
        if row.owner_id != viewer.id:
            raise AuthorizationError(message=_("Only the list's owner can change it"))
        return row

    async def _item(self, w: Wishlist, item_id: uuid.UUID, *, lock: bool = False) -> WishlistItem:
        item = await self._repo.item(w.id, item_id, lock=lock)
        if item is None:
            raise NotFoundError(message=_("Item not found"))
        return item

    # -- reads -----------------------------------------------------------------

    async def list(
        self,
        viewer: User,
        owner_id: uuid.UUID | None = None,
        household_id: uuid.UUID | None = None,
    ) -> list[WishlistOut]:
        """@brief Wishlists the viewer may see, optionally one person's or pet's."""
        rows = await self._repo.visible(
            viewer.id, self._cid, owner_id=owner_id, household_id=household_id
        )
        return await self._summaries(rows, viewer)

    async def get(self, wishlist_id: uuid.UUID, viewer: User) -> WishlistDetail:
        """@brief One wishlist with items; claim counts hidden from the owner."""
        w = await self._visible(wishlist_id, viewer)
        items = await self._repo.items(w.id)
        owner = w.owner_id == viewer.id
        totals = {} if owner else await self._repo.claim_totals([i.id for i in items], viewer.id)
        (summary,) = await self._summaries([(w, len(items))], viewer)
        return WishlistDetail(
            **summary.model_dump(),
            items=[
                ItemOut(
                    id=i.id,
                    name=i.name,
                    url=i.url,
                    price=i.price,
                    notes=i.notes,
                    qty=i.qty,
                    claimed=None if owner else totals.get(i.id, (0, 0))[0],
                    mine=None if owner else totals.get(i.id, (0, 0))[1],
                )
                for i in items
            ],
        )

    # -- owner writes ------------------------------------------------------------

    async def create(self, body: WishlistCreate, owner: User) -> WishlistDetail:
        """@brief New list; a household list must be for someone you manage."""
        if body.household_id and not await self._repo.owned_household(
            body.household_id, owner.id, self._cid
        ):
            raise NotFoundError(message=_("Household member not found"))
        if len(await self._repo.visible(owner.id, self._cid, owner_id=owner.id)) >= MAX_LISTS:
            raise ValidationError(message=_("You have reached the wishlist limit"))
        w = await self._repo.create(community_id=self._cid, owner_id=owner.id, **body.model_dump())
        return await self.get(w.id, owner)

    async def update(
        self, wishlist_id: uuid.UUID, body: WishlistUpdate, owner: User
    ) -> WishlistDetail:
        """@brief Edit title, occasion, date, note or visibility."""
        w = await self._owned(wishlist_id, owner)
        values: dict[str, Any] = body.model_dump(exclude_unset=True)
        if values.get("title") is None:
            values.pop("title", None)
        if values:
            await self._repo.update(w, values)
        return await self.get(w.id, owner)

    async def delete(self, wishlist_id: uuid.UUID, owner: User) -> None:
        """@brief Remove a list."""
        await self._repo.soft_delete(await self._owned(wishlist_id, owner))

    async def add_item(self, wishlist_id: uuid.UUID, body: ItemIn, owner: User) -> WishlistDetail:
        """@brief Add a wish."""
        w = await self._owned(wishlist_id, owner)
        if len(await self._repo.items(w.id)) >= MAX_ITEMS:
            raise ValidationError(message=_("This list is full"))
        await self._repo.add_item(community_id=self._cid, wishlist_id=w.id, **body.model_dump())
        return await self.get(w.id, owner)

    async def update_item(
        self, wishlist_id: uuid.UUID, item_id: uuid.UUID, body: ItemUpdate, owner: User
    ) -> WishlistDetail:
        """@brief Edit a wish."""
        w = await self._owned(wishlist_id, owner)
        values = body.model_dump(exclude_unset=True)
        for k in ("name", "qty"):
            if values.get(k) is None:
                values.pop(k, None)
        await self._repo.update(await self._item(w, item_id), values)
        return await self.get(w.id, owner)

    async def delete_item(self, wishlist_id: uuid.UUID, item_id: uuid.UUID, owner: User) -> None:
        """@brief Remove a wish."""
        w = await self._owned(wishlist_id, owner)
        await self._repo.soft_delete(await self._item(w, item_id))

    # -- gift-giver writes -------------------------------------------------------

    async def claim(
        self, wishlist_id: uuid.UUID, item_id: uuid.UUID, qty: int, viewer: User
    ) -> WishlistDetail:
        """@brief Say you will give ``qty`` of an item (replaces your earlier claim)."""
        w = await self._visible(wishlist_id, viewer)
        if w.owner_id == viewer.id:
            raise ValidationError(message=_("You can't claim gifts on your own list"))
        item = await self._item(w, item_id, lock=True)
        total, mine = (await self._repo.claim_totals([item.id], viewer.id)).get(item.id, (0, 0))
        left = item.qty - (total - mine)
        if qty > left:
            raise ValidationError(
                message=_("Only %(n)s left to claim") % {"n": max(left, 0)},
                details={"remaining": max(left, 0)},
            )
        await self._repo.set_claim(item, viewer.id, qty, self._cid)
        return await self.get(w.id, viewer)

    async def release(
        self, wishlist_id: uuid.UUID, item_id: uuid.UUID, viewer: User
    ) -> WishlistDetail:
        """@brief Take back your claim."""
        w = await self._visible(wishlist_id, viewer)
        await self._repo.release((await self._item(w, item_id)).id, viewer.id)
        return await self.get(w.id, viewer)
