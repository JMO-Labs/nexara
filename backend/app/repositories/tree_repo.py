"""
@file tree_repo.py
@brief Lookups the tree needs on top of RelationRepository: group
       members, settings in bulk and household members regardless of
       visibility (the service decides who is masked).
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.household import HouseholdMember
from app.models.subgroup import Subgroup, SubgroupMember
from app.models.user import User
from app.models.user_settings import UserSettings


class TreeRepository:
    """@brief Read-only queries for the tree."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def group_by_slug(self, slug: str, community_id: uuid.UUID) -> Subgroup | None:
        """@brief Live (not archived) group by slug."""
        stmt = select(Subgroup).where(
            Subgroup.slug == slug,
            Subgroup.community_id == community_id,
            Subgroup.archived_at.is_(None),
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def group_member_ids(self, subgroup_id: uuid.UUID) -> set[uuid.UUID]:
        """@brief Active users in the group."""
        stmt = (
            select(SubgroupMember.user_id)
            .join(User, User.id == SubgroupMember.user_id)
            .where(
                SubgroupMember.subgroup_id == subgroup_id,
                User.deleted_at.is_(None),
                User.is_active.is_(True),
            )
        )
        return set((await self._session.execute(stmt)).scalars().all())

    async def settings_for(self, ids: list[uuid.UUID]) -> dict[uuid.UUID, UserSettings]:
        """@brief Settings rows by user id."""
        if not ids:
            return {}
        stmt = select(UserSettings).where(UserSettings.user_id.in_(ids))
        return {s.user_id: s for s in (await self._session.execute(stmt)).scalars().all()}

    async def members_live(
        self, ids: list[uuid.UUID], community_id: uuid.UUID
    ) -> dict[uuid.UUID, HouseholdMember]:
        """@brief Non-deleted household members, whatever their visibility."""
        if not ids:
            return {}
        stmt = select(HouseholdMember).where(
            HouseholdMember.id.in_(ids),
            HouseholdMember.community_id == community_id,
            HouseholdMember.deleted_at.is_(None),
        )
        return {m.id: m for m in (await self._session.execute(stmt)).scalars().all()}
