"""
@file wishlist_repo.py
@brief Wishlists and their recipients. A viewer sees a list when its level
       allows (``level_visible``), or when they are a recipient themselves or
       a member of a recipient group.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, delete, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.household import HouseholdMember
from app.models.subgroup import Subgroup, SubgroupMember
from app.models.user import User
from app.models.wishlist import Wishlist, WishlistItem, WishlistRecipient
from app.repositories.household_repo import household_visible, level_visible
from app.repositories.visibility_preds import not_blocked

R = WishlistRecipient


def _recipient(kind: str, ref: Any) -> Any:
    return exists().where(R.wishlist_id == Wishlist.id, R.kind == kind, R.ref_id == ref)


def wishlist_visible(viewer_id: uuid.UUID, community_id: uuid.UUID) -> Any:
    """@brief Live wishlist the viewer may see."""
    in_group = exists().where(
        R.wishlist_id == Wishlist.id,
        R.kind == "subgroup",
        SubgroupMember.subgroup_id == R.ref_id,
        SubgroupMember.user_id == viewer_id,
    )
    return and_(
        Wishlist.community_id == community_id,
        Wishlist.deleted_at.is_(None),
        not_blocked(Wishlist.owner_id, viewer_id),
        or_(
            level_visible(Wishlist.visibility, Wishlist.owner_id, viewer_id),
            _recipient("user", viewer_id),
            in_group,
            # A list "for everyone" (reunion, BBQ) is open to the whole community.
            exists().where(R.wishlist_id == Wishlist.id, R.kind == "everyone"),
        ),
    )


class WishlistRepository:
    """@brief Data access for wishlists and wishlist_recipients."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def visible(
        self,
        viewer_id: uuid.UUID,
        community_id: uuid.UUID,
        *,
        person_id: uuid.UUID | None = None,
        household_id: uuid.UUID | None = None,
        owner_id: uuid.UUID | None = None,
    ) -> list[tuple[Wishlist, int]]:
        """
        @brief Visible wishlists with live item counts, soonest event first.
        @param person_id lists made by or for this member
        @param household_id lists for this household member/pet
        @param owner_id lists made by this member
        """
        count = (
            select(func.count(WishlistItem.id))
            .where(WishlistItem.wishlist_id == Wishlist.id, WishlistItem.deleted_at.is_(None))
            .scalar_subquery()
        )
        stmt = select(Wishlist, count).where(wishlist_visible(viewer_id, community_id))
        if person_id is not None:
            stmt = stmt.where(or_(Wishlist.owner_id == person_id, _recipient("user", person_id)))
        if household_id is not None:
            stmt = stmt.where(_recipient("household", household_id))
        if owner_id is not None:
            stmt = stmt.where(Wishlist.owner_id == owner_id)
        stmt = stmt.order_by(Wishlist.event_date.asc().nulls_last(), Wishlist.created_at.desc())
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

    async def update(self, row: Any, values: dict[str, Any]) -> Any:
        """@brief Apply field updates to any wishlist row."""
        for k, v in values.items():
            setattr(row, k, v)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def soft_delete(self, row: Any) -> None:
        """@brief Mark deleted."""
        row.deleted_at = datetime.now(UTC)
        await self._session.flush()

    # -- recipients ----------------------------------------------------------

    async def recipients(self, wishlist_ids: list[uuid.UUID]) -> list[WishlistRecipient]:
        """@brief Recipients of these lists."""
        if not wishlist_ids:
            return []
        stmt = select(R).where(R.wishlist_id.in_(wishlist_ids)).order_by(R.kind, R.name)
        return list((await self._session.execute(stmt)).scalars())

    async def replace_recipients(self, wishlist: Wishlist, rows: list[dict[str, Any]]) -> None:
        """@brief Make the list's recipients exactly ``rows``."""
        await self._session.execute(delete(R).where(R.wishlist_id == wishlist.id))
        for r in rows:
            self._session.add(R(wishlist_id=wishlist.id, community_id=wishlist.community_id, **r))
        await self._session.flush()

    async def is_recipient(self, wishlist_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """@brief The member is a named recipient of the list."""
        stmt = select(
            exists().where(R.wishlist_id == wishlist_id, R.kind == "user", R.ref_id == user_id)
        )
        return bool((await self._session.execute(stmt)).scalar())

    async def user_names(
        self, ids: list[uuid.UUID], community_id: uuid.UUID
    ) -> dict[uuid.UUID, str]:
        """@brief Display names of active members."""
        if not ids:
            return {}
        stmt = select(User.id, User.display_name).where(
            User.id.in_(ids), User.community_id == community_id, User.deleted_at.is_(None)
        )
        return {i: n for i, n in (await self._session.execute(stmt)).all()}

    async def household_names(
        self, ids: list[uuid.UUID], viewer_id: uuid.UUID, community_id: uuid.UUID
    ) -> dict[uuid.UUID, tuple[str, str]]:
        """@brief (name, kind) of household members the viewer may see."""
        if not ids:
            return {}
        stmt = select(HouseholdMember.id, HouseholdMember.name, HouseholdMember.kind).where(
            HouseholdMember.id.in_(ids), household_visible(viewer_id, community_id)
        )
        return {i: (n, k) for i, n, k in (await self._session.execute(stmt)).all()}

    async def my_group_ids(self, user_id: uuid.UUID, ids: list[uuid.UUID]) -> set[uuid.UUID]:
        """@brief Which of ``ids`` the member belongs to."""
        if not ids:
            return set()
        stmt = select(SubgroupMember.subgroup_id).where(
            SubgroupMember.user_id == user_id, SubgroupMember.subgroup_id.in_(ids)
        )
        return set((await self._session.execute(stmt)).scalars())

    async def group_names(
        self, ids: list[uuid.UUID], community_id: uuid.UUID
    ) -> dict[uuid.UUID, tuple[str, str]]:
        """@brief (name, slug) of live groups."""
        if not ids:
            return {}
        stmt = select(Subgroup.id, Subgroup.name, Subgroup.slug).where(
            Subgroup.id.in_(ids),
            Subgroup.community_id == community_id,
            Subgroup.archived_at.is_(None),
        )
        return {i: (n, s) for i, n, s in (await self._session.execute(stmt)).all()}
