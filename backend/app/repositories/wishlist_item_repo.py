"""
@file wishlist_item_repo.py
@brief Wishlist items (gifts and cash funds), claims and link previews.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.link_preview import LinkPreview
from app.models.user import User
from app.models.wishlist import Wishlist, WishlistClaim, WishlistItem

C = WishlistClaim


class WishlistItemRepository:
    """@brief Data access for wishlist_items and wishlist_claims."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def items(self, wishlist_id: uuid.UUID) -> list[WishlistItem]:
        """@brief Live items in display order."""
        stmt = (
            select(WishlistItem)
            .where(WishlistItem.wishlist_id == wishlist_id, WishlistItem.deleted_at.is_(None))
            .order_by(WishlistItem.position, WishlistItem.created_at)
        )
        return list((await self._session.execute(stmt)).scalars())

    async def item(
        self, wishlist_id: uuid.UUID, item_id: uuid.UUID, *, lock: bool = False
    ) -> WishlistItem | None:
        """@brief One live item of a wishlist (row-locked for claims)."""
        stmt = select(WishlistItem).where(
            WishlistItem.id == item_id,
            WishlistItem.wishlist_id == wishlist_id,
            WishlistItem.deleted_at.is_(None),
        )
        if lock:
            stmt = stmt.with_for_update()
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def add(self, **values: Any) -> WishlistItem:
        """@brief Insert an item at the end."""
        pos = (
            await self._session.execute(
                select(func.coalesce(func.max(WishlistItem.position), -1) + 1).where(
                    WishlistItem.wishlist_id == values["wishlist_id"]
                )
            )
        ).scalar_one()
        row = WishlistItem(position=pos, **values)
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def update(self, item: WishlistItem, values: dict[str, Any]) -> WishlistItem:
        """@brief Apply field updates to an item."""
        for k, v in values.items():
            setattr(item, k, v)
        await self._session.flush()
        await self._session.refresh(item)
        return item

    async def soft_delete(self, item: WishlistItem) -> None:
        """@brief Mark an item deleted."""
        item.deleted_at = datetime.now(UTC)
        await self._session.flush()

    async def linked_for_refresh(
        self,
        *,
        ids: list[uuid.UUID] | None = None,
        amazon_before: datetime | None = None,
        other_before: datetime | None = None,
        limit: int = 50,
    ) -> list[tuple[WishlistItem, str]]:
        """
        @brief Live gift items with a link, with their list's currency.
        @param ids exactly these items; otherwise items whose shop data is
               missing or older than the cutoffs (Amazon vs other shops)
        """
        amazon = WishlistItem.url.ilike("%amazon.%")
        stmt = (
            select(WishlistItem, Wishlist.currency)
            .join(Wishlist, Wishlist.id == WishlistItem.wishlist_id)
            .outerjoin(LinkPreview, LinkPreview.id == WishlistItem.preview_id)
            .where(
                WishlistItem.url.is_not(None),
                WishlistItem.deleted_at.is_(None),
                WishlistItem.kind == "gift",
                Wishlist.deleted_at.is_(None),
            )
            .order_by(LinkPreview.fetched_at.asc().nulls_first())
            .limit(limit)
        )
        if ids is not None:
            stmt = stmt.where(WishlistItem.id.in_(ids))
        else:
            stmt = stmt.where(
                or_(
                    LinkPreview.id.is_(None),
                    and_(amazon, LinkPreview.fetched_at < amazon_before),
                    and_(~amazon, LinkPreview.fetched_at < other_before),
                )
            )
        return [(i, c) for i, c in (await self._session.execute(stmt)).all()]

    async def previews(self, ids: list[uuid.UUID]) -> dict[uuid.UUID, LinkPreview]:
        """@brief Link previews by id."""
        if not ids:
            return {}
        stmt = select(LinkPreview).where(LinkPreview.id.in_(ids))
        return {p.id: p for p in (await self._session.execute(stmt)).scalars()}

    # -- claims --------------------------------------------------------------

    async def claims(self, item_ids: list[uuid.UUID]) -> list[tuple[WishlistClaim, str]]:
        """@brief Claims on these items with the claimer's display name."""
        if not item_ids:
            return []
        stmt = (
            select(C, User.display_name)
            .join(User, User.id == C.user_id)
            .where(C.item_id.in_(item_ids))
            .order_by(C.created_at)
        )
        return [(c, n) for c, n in (await self._session.execute(stmt)).all()]

    async def set_claim(
        self,
        item: WishlistItem,
        user_id: uuid.UUID,
        qty: int,
        amount_cents: int | None,
        community_id: uuid.UUID,
    ) -> None:
        """@brief Replace the user's claim on an item (caller holds the item lock)."""
        await self.release(item.id, user_id)
        self._session.add(
            C(
                item_id=item.id,
                user_id=user_id,
                qty=qty,
                amount_cents=amount_cents,
                community_id=community_id,
            )
        )
        await self._session.flush()

    async def release(self, item_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """@brief Delete the user's claim; True when one existed."""
        res = await self._session.execute(
            delete(C).where(C.item_id == item_id, C.user_id == user_id)
        )
        return bool(getattr(res, "rowcount", 0))
