"""
@file celebration_repo.py
@brief Birthdays the viewer may see: members who share theirs with the
       community (plus the viewer's own), block-filtered.
"""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.household import HouseholdMember
from app.models.user import User
from app.models.user_settings import UserSettings
from app.repositories.household_repo import household_visible
from app.repositories.visibility_preds import not_blocked


class CelebrationRepository:
    """@brief Read-only birthday lookups, scoped to one community."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def user_birthdays(
        self, community_id: uuid.UUID, viewer_id: uuid.UUID
    ) -> list[tuple[uuid.UUID, str, str, date]]:
        """@return (id, username, display_name, birthday) for visible birthdays"""
        shown = func.coalesce(UserSettings.show_birthday_to, "community")
        stmt = (
            select(User.id, User.username, User.display_name, User.birthday)
            .outerjoin(UserSettings, UserSettings.user_id == User.id)
            .where(
                User.community_id == community_id,
                User.deleted_at.is_(None),
                User.is_active.is_(True),
                User.birthday.is_not(None),
                or_(User.id == viewer_id, shown == "community"),
                not_blocked(User.id, viewer_id),
            )
        )
        return [(r[0], r[1], r[2], r[3]) for r in (await self._session.execute(stmt)).all()]

    async def celebratable_user(
        self, community_id: uuid.UUID, actor_id: uuid.UUID, user_id: uuid.UUID
    ) -> User | None:
        """@brief A live member the actor has no block with."""
        stmt = select(User).where(
            User.id == user_id,
            User.community_id == community_id,
            User.deleted_at.is_(None),
            User.is_active.is_(True),
            not_blocked(User.id, actor_id),
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def celebratable_household(
        self, community_id: uuid.UUID, actor_id: uuid.UUID, member_id: uuid.UUID
    ) -> HouseholdMember | None:
        """@brief A household member/pet the actor may see."""
        stmt = select(HouseholdMember).where(
            HouseholdMember.id == member_id, household_visible(actor_id, community_id)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()
