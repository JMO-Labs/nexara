"""
@file group_tag_repo.py
@brief @group tags: resolve group slugs, the actor's role in a group and the
       members to notify (minus the actor and anyone in a block with them).
"""

from __future__ import annotations

import uuid

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.moderation import UserBlock
from app.models.subgroup import Subgroup, SubgroupMember
from app.models.user import User


class GroupTagRepository:
    """@brief Data access for @group tags."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def by_slugs(self, community_id: uuid.UUID, slugs: list[str]) -> list[Subgroup]:
        """@brief Active (not archived) groups with these slugs in the community."""
        if not slugs:
            return []
        stmt = select(Subgroup).where(
            Subgroup.community_id == community_id,
            Subgroup.slug.in_(slugs),
            Subgroup.archived_at.is_(None),
        )
        return list((await self._session.execute(stmt)).scalars())

    async def roles(
        self, user_id: uuid.UUID, subgroup_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, str]:
        """@brief The user's role in each of these groups (absent = not a member)."""
        if not subgroup_ids:
            return {}
        stmt = select(SubgroupMember.subgroup_id, SubgroupMember.role).where(
            SubgroupMember.user_id == user_id, SubgroupMember.subgroup_id.in_(subgroup_ids)
        )
        return {sid: role for sid, role in (await self._session.execute(stmt)).all()}

    async def get(self, subgroup_id: uuid.UUID, community_id: uuid.UUID) -> Subgroup | None:
        """@brief One group in the community."""
        stmt = select(Subgroup).where(
            Subgroup.id == subgroup_id, Subgroup.community_id == community_id
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def recipients(
        self, subgroup_id: uuid.UUID, community_id: uuid.UUID, actor_id: uuid.UUID
    ) -> list[uuid.UUID]:
        """@brief Active members except the actor and anyone blocking/blocked by them."""
        blocked = select(UserBlock.id).where(
            or_(
                and_(UserBlock.blocker_id == actor_id, UserBlock.blocked_id == User.id),
                and_(UserBlock.blocked_id == actor_id, UserBlock.blocker_id == User.id),
            )
        )
        stmt = (
            select(User.id)
            .join(SubgroupMember, SubgroupMember.user_id == User.id)
            .where(
                SubgroupMember.subgroup_id == subgroup_id,
                User.community_id == community_id,
                User.id != actor_id,
                User.deleted_at.is_(None),
                User.is_active.is_(True),
                ~blocked.exists(),
            )
            .order_by(User.id)
        )
        return list((await self._session.execute(stmt)).scalars())
