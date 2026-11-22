"""
@file wishlist_gift_service.py
@brief Wishes (gifts and cash funds) and claims. Owners and member
       recipients edit wishes; givers claim what's left within the list's
       per-giver cap. Shopping links get a preview fetched in the background.
"""

from __future__ import annotations

import uuid

import structlog

from app.core.exceptions import AuthorizationError, NotFoundError, ValidationError
from app.core.i18n import _
from app.models.user import User
from app.models.wishlist import Wishlist, WishlistItem
from app.repositories.wishlist_item_repo import WishlistItemRepository
from app.schemas.wishlist import ClaimIn, ItemIn, ItemUpdate, WishlistDetail
from app.services.wishlist_service import WishlistService
from app.services.wishlist_view import claim_value

logger = structlog.get_logger(__name__)
MAX_ITEMS = 150


def money(cents: int, currency: str) -> str:
    """@brief "12.50 USD" style amount for messages."""
    return f"{cents / 100:,.2f} {currency}"


class WishlistGiftService:
    """@brief Wish and claim rules on top of WishlistService."""

    def __init__(
        self, lists: WishlistService, items: WishlistItemRepository, community_id: uuid.UUID
    ) -> None:
        self._lists = lists
        self._items = items
        self._cid = community_id

    async def _editable(self, wishlist_id: uuid.UUID, viewer: User) -> Wishlist:
        w = await self._lists.visible(wishlist_id, viewer)
        if not (await self._lists.access(w, viewer)).can_edit_items:
            raise AuthorizationError(message=_("Only the list's people can change wishes"))
        return w

    async def _item(self, w: Wishlist, item_id: uuid.UUID, *, lock: bool = False) -> WishlistItem:
        item = await self._items.item(w.id, item_id, lock=lock)
        if item is None:
            raise NotFoundError(message=_("Item not found"))
        return item

    def _preview(self, item: WishlistItem) -> None:
        """@brief Queue a link preview; never fails the request."""
        if not item.url:
            return
        try:
            from app.tasks.shop_tasks import fetch_shop_item

            fetch_shop_item.apply_async(args=(str(item.id),), countdown=2)
        except Exception:
            logger.warning("wishlist_preview_enqueue_failed", item_id=str(item.id))

    # -- wishes ------------------------------------------------------------------

    async def add_item(self, wishlist_id: uuid.UUID, body: ItemIn, viewer: User) -> WishlistDetail:
        """@brief Add a gift or fund."""
        w = await self._editable(wishlist_id, viewer)
        if len(await self._items.items(w.id)) >= MAX_ITEMS:
            raise ValidationError(message=_("This list is full"))
        item = await self._items.add(community_id=self._cid, wishlist_id=w.id, **body.model_dump())
        self._preview(item)
        return await self._lists.get(w.id, viewer)

    async def update_item(
        self, wishlist_id: uuid.UUID, item_id: uuid.UUID, body: ItemUpdate, viewer: User
    ) -> WishlistDetail:
        """@brief Edit a wish."""
        w = await self._editable(wishlist_id, viewer)
        item = await self._item(w, item_id)
        values = body.model_dump(exclude_unset=True)
        for k in ("name", "qty"):
            if values.get(k) is None:
                values.pop(k, None)
        if item.kind == "fund":
            values.pop("price_cents", None)
            values.pop("qty", None)
        relink = "url" in values and values["url"] != item.url
        if relink:
            values["preview_id"] = None
        if "price_cents" in values:
            values["price_auto"] = False  # a typed price stops following the shop
        await self._items.update(item, values)
        if relink:
            self._preview(item)
        return await self._lists.get(w.id, viewer)

    async def delete_item(self, wishlist_id: uuid.UUID, item_id: uuid.UUID, viewer: User) -> None:
        """@brief Remove a wish."""
        w = await self._editable(wishlist_id, viewer)
        await self._items.soft_delete(await self._item(w, item_id))

    # -- claims ------------------------------------------------------------------

    async def claim(
        self, wishlist_id: uuid.UUID, item_id: uuid.UUID, body: ClaimIn, viewer: User
    ) -> WishlistDetail:
        """@brief Give ``qty`` of a gift, or pledge ``amount_cents`` to a fund."""
        w = await self._lists.visible(wishlist_id, viewer)
        if not (await self._lists.access(w, viewer)).sees_claims(w):
            raise ValidationError(message=_("You can't claim gifts on a list for you"))
        item = await self._item(w, item_id, lock=True)
        claims = await self._items.claims([i.id for i in await self._items.items(w.id)])
        others = [c for c, _n in claims if c.item_id == item.id and c.user_id != viewer.id]
        if item.kind == "fund":
            if body.amount_cents is None:
                raise ValidationError(message=_("Enter an amount"))
            qty, amount = 1, body.amount_cents
            left = (item.goal_cents or 0) - sum(c.amount_cents or 0 for c in others)
            if amount > left:
                raise ValidationError(
                    message=_("Only %(m)s left to reach the goal")
                    % {"m": money(max(left, 0), w.currency)},
                    details={"remaining_cents": max(left, 0)},
                )
        else:
            qty, amount = body.qty, None
            left = item.qty - sum(c.qty for c in others)
            if qty > left:
                raise ValidationError(
                    message=_("Only %(n)s left to claim") % {"n": max(left, 0)},
                    details={"remaining": max(left, 0)},
                )
        if w.giver_cap_cents is not None:
            items = {i.id: i for i in await self._items.items(w.id)}
            spent = sum(
                claim_value(items[c.item_id], c.qty, c.amount_cents)
                for c, _n in claims
                if c.user_id == viewer.id and c.item_id != item.id and c.item_id in items
            )
            if spent + claim_value(item, qty, amount) > w.giver_cap_cents:
                raise ValidationError(
                    message=_("That's over this list's limit of %(m)s per person")
                    % {"m": money(w.giver_cap_cents, w.currency)},
                    details={"cap_cents": w.giver_cap_cents, "spent_cents": spent},
                )
        await self._items.set_claim(item, viewer.id, qty, amount, self._cid)
        return await self._lists.get(w.id, viewer)

    async def release(
        self, wishlist_id: uuid.UUID, item_id: uuid.UUID, viewer: User
    ) -> WishlistDetail:
        """@brief Take back your claim."""
        w = await self._lists.visible(wishlist_id, viewer)
        await self._items.release((await self._item(w, item_id)).id, viewer.id)
        return await self._lists.get(w.id, viewer)
