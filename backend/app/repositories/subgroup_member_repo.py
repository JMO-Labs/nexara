"""
@file subgroup_member_repo.py
@brief Repository for subgroup membership records.

Split from subgroup_repo.py; ``SubgroupMemberRepository`` is re-exported there.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select

from app.models.subgroup import Subgroup, SubgroupMember
from app.models.user import User
from app.repositories.base import BaseRepository


class SubgroupMemberRepository(BaseRepository[SubgroupMember]):
    """
    @brief Async repository for subgroup membership records.

    @param session Async SQLAlchemy session.
    """

    model = SubgroupMember

    async def get_membership(
        self,
        subgroup_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> SubgroupMember | None:
        """
        @brief Fetch a single membership row.

        @param subgroup_id Subgroup ID.
        @param user_id User ID.
        @return The SubgroupMember or None.
        """
        stmt = select(SubgroupMember).where(
            SubgroupMember.subgroup_id == subgroup_id,
            SubgroupMember.user_id == user_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_my_roles(
        self,
        user_id: uuid.UUID,
    ) -> dict[uuid.UUID, str]:
        """
        @brief Map subgroup_id -> role for every direct membership of user_id.
        @return Dict keyed by subgroup_id with role value.
        """
        stmt = select(SubgroupMember.subgroup_id, SubgroupMember.role).where(
            SubgroupMember.user_id == user_id,
        )
        result = await self._session.execute(stmt)
        return {sid: role for sid, role in result.all()}

    async def add_member(
        self,
        *,
        community_id: uuid.UUID,
        subgroup_id: uuid.UUID,
        user_id: uuid.UUID,
        role: str = "member",
        invited_by: uuid.UUID | None = None,
    ) -> SubgroupMember:
        """
        @brief Add a membership row.

        @return The created SubgroupMember.
        """
        member = SubgroupMember(
            community_id=community_id,
            subgroup_id=subgroup_id,
            user_id=user_id,
            role=role,
            invited_by=invited_by,
        )
        self._session.add(member)
        await self._session.flush()
        await self._session.refresh(member)
        return member

    async def remove_member(
        self,
        subgroup_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """
        @brief Delete a membership row.

        @param subgroup_id Subgroup ID.
        @param user_id User ID.
        @return True if a row was deleted, False otherwise.
        """
        membership = await self.get_membership(subgroup_id, user_id)
        if membership is None:
            return False
        await self._session.delete(membership)
        await self._session.flush()
        return True

    async def update_role(
        self,
        membership: SubgroupMember,
        role: str,
    ) -> SubgroupMember:
        """
        @brief Update a member's role in place.

        @param membership The membership ORM instance.
        @param role New role string.
        @return The updated instance.
        """
        membership.role = role
        await self._session.flush()
        await self._session.refresh(membership)
        return membership

    async def count_for_user(
        self,
        user_id: uuid.UUID,
        community_id: uuid.UUID,
    ) -> int:
        """
        @brief Count active memberships for a user.

        Archived subgroups do not count toward the user's limit.

        @param user_id User ID.
        @param community_id Community scope.
        @return Integer count.
        """
        stmt = (
            select(func.count(SubgroupMember.subgroup_id))
            .select_from(SubgroupMember)
            .join(Subgroup, Subgroup.id == SubgroupMember.subgroup_id)
            .where(
                SubgroupMember.user_id == user_id,
                Subgroup.community_id == community_id,
                Subgroup.archived_at.is_(None),
            )
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one() or 0)

    async def count_members(self, subgroup_id: uuid.UUID) -> int:
        """
        @brief Count all members in a subgroup.

        @param subgroup_id Subgroup ID.
        @return Integer count.
        """
        stmt = select(func.count(SubgroupMember.user_id)).where(
            SubgroupMember.subgroup_id == subgroup_id,
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one() or 0)

    async def list_members(
        self,
        subgroup_id: uuid.UUID,
    ) -> list[tuple[SubgroupMember, User]]:
        """
        @brief List members of a subgroup joined against users.

        @param subgroup_id Subgroup ID.
        @return List of ``(SubgroupMember, User)`` tuples ordered by
        joined_at DESC.
        """
        stmt = (
            select(SubgroupMember, User)
            .join(User, User.id == SubgroupMember.user_id)
            .where(
                SubgroupMember.subgroup_id == subgroup_id,
                User.deleted_at.is_(None),
            )
            .order_by(SubgroupMember.joined_at.desc())
        )
        result = await self._session.execute(stmt)
        return [(m, u) for m, u in result.all()]
