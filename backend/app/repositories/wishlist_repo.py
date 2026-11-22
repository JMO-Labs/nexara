"""
@file wishlist_repo.py
@brief Wishlists, their items and claims. Visibility reuses the profile
       levels (private, groups, community) via ``level_visible``.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, delete, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.household import HouseholdMember
from app.models.wishlist import Wishlist, WishlistClaim, WishlistItem
from app.repositories.household_repo import level_visible
from app.repositories.visibility_preds import not_blocked


def wishlist_visible(viewer_id: uuid.UUID, community_id: uuid.UUID) -> Any:
    """@brief Live wishlist the viewer may see (its household member still live)."""
    return and_(
        Wishlist.community_id == community_id,
        Wishlist.deleted_at.is_(None),
        level_visible(Wishlist.visibility, Wishlist.owner_id, viewer_id),
        not_blocked(Wishlist.owner_id, viewer_id),
        or_(
            Wishlist.household_id.is_(None),
            exists().where(
                HouseholdMember.id == Wishlist.household_id, HouseholdMember.deleted_at.is_(None)
            ),
        ),
    )


class WishlistRepository:
    """@brief Data access for wishlists, wishlist_items and wishlist_claims."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # -- lists ---------------------------------------------------------------

    async def visible(
        self,
        viewer_id: uuid.UUID,
        community_id: uuid.UUID,
        *,
        owner_id: uuid.UUID | None = None,
        household_id: uuid.UUID | None = None,
    ) -> list[tuple[Wishlist, int]]:
        """@brief Visible wishlists with their live item counts, soonest occasion first."""
        count = (
            select(func.count(WishlistItem.id))
            .where(WishlistItem.wishlist_id == Wishlist.id, WishlistItem.deleted_at.is_(None))
            .scalar_subquery()
        )
        stmt = select(Wishlist, count).where(wishlist_visible(viewer_id, community_id))
        if owner_id is not None:
            stmt = stmt.where(Wishlist.owner_id == owner_id)
        if household_id is not None:
            stmt = stmt.where(Wishlist.household_id == household_id)
        stmt = stmt.order_by(Wishlist.occasion_date.asc().nulls_last(), Wishlist.created_at.desc())
        return [(w, n) for w, n in (await self._session.execute(stmt)).all()]

    async def get_visible(
        self, wishlist_id: uuid.UUID, viewer_id: uuid.UUID, community_id: uuid.UUID
    ) -> Wishlist | None:
        """@brief One wishlist if the viewer may see it."""
        stmt = select(Wishlist).where(
            Wishlist.id == wishlist_id, wishlist_visible(viewer_id, community_id)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def create(self, **values: Any) -> Wishlist:
        """@brief Insert a wishlist."""
        row = Wishlist(**values)
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def update(self, row: Wishlist | WishlistItem, values: dict[str, Any]) -> Any:
        """@brief Apply field updates to a wishlist or item."""
        for k, v in values.items():
            setattr(row, k, v)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def soft_delete(self, row: Wishlist | WishlistItem) -> None:
        """@brief Mark deleted."""
        row.deleted_at = datetime.now(UTC)
        await self._session.flush()

    async def owned_household(
        self, household_id: uuid.UUID, owner_id: uuid.UUID, community_id: uuid.UUID
    ) -> HouseholdMember | None:
        """@brief A live household member managed by ``owner_id``."""
        stmt = select(HouseholdMember).where(
            HouseholdMember.id == household_id,
            HouseholdMember.owner_id == owner_id,
            HouseholdMember.community_id == community_id,
            HouseholdMember.deleted_at.is_(None),
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def household_names(self, ids: list[uuid.UUID]) -> dict[uuid.UUID, tuple[str, str]]:
        """@brief (name, kind) of household members by id."""
        if not ids:
            return {}
        stmt = select(HouseholdMember.id, HouseholdMember.name, HouseholdMember.kind).where(
            HouseholdMember.id.in_(ids)
        )
        return {i: (n, k) for i, n, k in (await self._session.execute(stmt)).all()}

    # -- items ---------------------------------------------------------------

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

    async def add_item(self, **values: Any) -> WishlistItem:
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

    # -- claims --------------------------------------------------------------

    async def claim_totals(
        self, item_ids: list[uuid.UUID], viewer_id: uuid.UUID
    ) -> dict[uuid.UUID, tuple[int, int]]:
        """@brief Per item: (claimed by anyone, claimed by the viewer)."""
        if not item_ids:
            return {}
        mine = func.coalesce(
            func.sum(WishlistClaim.qty).filter(WishlistClaim.user_id == viewer_id), 0
        )
        stmt = (
            select(WishlistClaim.item_id, func.sum(WishlistClaim.qty), mine)
            .where(WishlistClaim.item_id.in_(item_ids))
            .group_by(WishlistClaim.item_id)
        )
        return {i: (int(t), int(m)) for i, t, m in (await self._session.execute(stmt)).all()}

    async def set_claim(
        self, item: WishlistItem, user_id: uuid.UUID, qty: int, community_id: uuid.UUID
    ) -> None:
        """@brief Replace the user's claim on an item (caller holds the item lock)."""
        await self.release(item.id, user_id)
        self._session.add(
            WishlistClaim(item_id=item.id, user_id=user_id, qty=qty, community_id=community_id)
        )
        await self._session.flush()

    async def release(self, item_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """@brief Delete the user's claim; True when one existed."""
        res = await self._session.execute(
            delete(WishlistClaim).where(
                WishlistClaim.item_id == item_id, WishlistClaim.user_id == user_id
            )
        )
        return bool(getattr(res, "rowcount", 0))
