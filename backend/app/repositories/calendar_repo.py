"""
@file calendar_repo.py
@brief Repository for Calendar entities.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select

from app.models.calendar import Calendar
from app.models.subgroup import SubgroupMember
from app.repositories.base import BaseRepository


class CalendarRepository(BaseRepository[Calendar]):
    """@brief Async repo for calendars (personal/community/subgroup)."""

    model = Calendar

    async def list_for_user(self, community_id: uuid.UUID, user_id: uuid.UUID) -> list[Calendar]:
        """
        @brief Calendars visible to a user.

        Includes: community calendar(s), the user's personal calendar, and
        subgroup calendars for subgroups the user belongs to.

        @param community_id Community scope.
        @param user_id Viewer.
        @return Ordered list (community → personal → subgroup).
        """
        sg_stmt = select(SubgroupMember.subgroup_id).where(
            SubgroupMember.user_id == user_id,
        )
        sg_result = await self._session.execute(sg_stmt)
        sg_ids = list(sg_result.scalars().all())

        stmt = select(Calendar).where(
            Calendar.community_id == community_id,
            Calendar.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        rows = list(result.scalars().all())

        out: list[Calendar] = []
        for cal in rows:
            if cal.kind == "community":
                out.append(cal)
            elif cal.kind == "personal" and cal.owner_id == user_id:
                out.append(cal)
            elif cal.kind == "subgroup" and cal.subgroup_id in sg_ids:
                out.append(cal)

        # Stable order: community first, then personal, then subgroup by name.
        rank = {"community": 0, "personal": 1, "subgroup": 2}
        out.sort(key=lambda c: (rank.get(c.kind, 3), c.name.lower()))
        return out

    async def get_personal(self, community_id: uuid.UUID, owner_id: uuid.UUID) -> Calendar | None:
        """@brief Fetch a user's personal calendar."""
        stmt = select(Calendar).where(
            Calendar.community_id == community_id,
            Calendar.kind == "personal",
            Calendar.owner_id == owner_id,
            Calendar.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_community(self, community_id: uuid.UUID) -> Calendar | None:
        """@brief Fetch the community-wide calendar."""
        stmt = select(Calendar).where(
            Calendar.community_id == community_id,
            Calendar.kind == "community",
            Calendar.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_for_subgroup(
        self, community_id: uuid.UUID, subgroup_id: uuid.UUID
    ) -> Calendar | None:
        """@brief Fetch a subgroup's calendar."""
        stmt = select(Calendar).where(
            Calendar.community_id == community_id,
            Calendar.kind == "subgroup",
            Calendar.subgroup_id == subgroup_id,
            Calendar.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def ensure_personal(
        self,
        community_id: uuid.UUID,
        owner_id: uuid.UUID,
        *,
        name: str = "Personal",
    ) -> Calendar:
        """@brief Idempotently create a personal calendar for a user."""
        existing = await self.get_personal(community_id, owner_id)
        if existing is not None:
            return existing
        cal = Calendar(
            community_id=community_id,
            kind="personal",
            owner_id=owner_id,
            name=name,
        )
        return await self.create(cal)

    async def ensure_community(
        self,
        community_id: uuid.UUID,
        *,
        name: str = "Community",
    ) -> Calendar:
        """@brief Idempotently create the community-wide calendar."""
        existing = await self.get_community(community_id)
        if existing is not None:
            return existing
        cal = Calendar(community_id=community_id, kind="community", name=name)
        return await self.create(cal)

    async def ensure_for_subgroup(
        self,
        community_id: uuid.UUID,
        subgroup_id: uuid.UUID,
        *,
        name: str,
    ) -> Calendar:
        """@brief Idempotently create a subgroup's calendar."""
        existing = await self.get_for_subgroup(community_id, subgroup_id)
        if existing is not None:
            return existing
        cal = Calendar(
            community_id=community_id,
            kind="subgroup",
            subgroup_id=subgroup_id,
            name=name,
        )
        return await self.create(cal)
