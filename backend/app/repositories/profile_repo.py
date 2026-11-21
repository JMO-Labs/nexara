"""
@file profile_repo.py
@brief Lookups for member profile privacy: target settings, shared groups.
"""

from __future__ import annotations

import uuid

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

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

    async def get_settings(self, user_id: uuid.UUID) -> UserSettings | None:
        """@brief The user's settings row, if any."""
        stmt = select(UserSettings).where(UserSettings.user_id == user_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def shares_group(self, a: uuid.UUID, b: uuid.UUID) -> bool:
        """@brief True when both users belong to at least one live subgroup."""
        mine, theirs = aliased(SubgroupMember), aliased(SubgroupMember)
        stmt = select(
            exists()
            .where(mine.user_id == a, theirs.user_id == b, mine.subgroup_id == theirs.subgroup_id)
            .where(Subgroup.id == mine.subgroup_id, Subgroup.archived_at.is_(None))
        )
        return bool((await self._session.execute(stmt)).scalar())
