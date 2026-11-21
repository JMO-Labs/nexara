"""
@file profile_repo.py
@brief Lookups for member profile privacy: target settings, shared groups.
"""

from __future__ import annotations

import uuid

from sqlalchemy import and_, exists, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models.moderation import UserBlock
from app.models.subgroup import Subgroup, SubgroupMember
from app.models.user import User
from app.models.user_settings import UserSettings


class ProfileRepository:
    """@brief Read-only queries backing ProfileService."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_user(self, user_id: uuid.UUID, community_id: uuid.UUID) -> User | None:
        """@brief Active, non-deleted user in the community."""
        stmt = select(User).where(
            User.id == user_id,
            User.community_id == community_id,
            User.deleted_at.is_(None),
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_by_username(self, username: str, community_id: uuid.UUID) -> User | None:
        """@brief Active, non-deleted user by username in the community."""
        stmt = select(User).where(
            User.username == username,
            User.community_id == community_id,
            User.deleted_at.is_(None),
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_settings(self, user_id: uuid.UUID) -> UserSettings | None:
        """@brief The user's settings row, if any."""
        stmt = select(UserSettings).where(UserSettings.user_id == user_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def shares_group(self, a: uuid.UUID, b: uuid.UUID) -> bool:
        """
        @brief True when both users belong to a live, gated subgroup.

        Open-join groups don't count: anyone could join one just to unlock
        "My groups" fields. Only invite-only / approval groups do.
        """
        mine, theirs = aliased(SubgroupMember), aliased(SubgroupMember)
        stmt = select(
            exists()
            .where(mine.user_id == a, theirs.user_id == b, mine.subgroup_id == theirs.subgroup_id)
            .where(
                Subgroup.id == mine.subgroup_id,
                Subgroup.archived_at.is_(None),
                Subgroup.join_policy != "open",
            )
        )
        return bool((await self._session.execute(stmt)).scalar())

    async def blocked_either_way(self, a: uuid.UUID, b: uuid.UUID) -> bool:
        """@brief True when either user has blocked the other."""
        stmt = select(
            exists().where(
                or_(
                    and_(UserBlock.blocker_id == a, UserBlock.blocked_id == b),
                    and_(UserBlock.blocker_id == b, UserBlock.blocked_id == a),
                )
            )
        )
        return bool((await self._session.execute(stmt)).scalar())
