"""
@file birthday_repo.py
@brief Queries for birthday reminders (users with a birthday today, recipients).
"""

from __future__ import annotations

import uuid

from sqlalchemy import extract, func, select

from app.models.user import User
from app.models.user_settings import UserSettings
from app.repositories.base import BaseRepository


class BirthdayRepository(BaseRepository[User]):
    """@brief Read-only birthday queries; community-scoped except discovery."""

    model = User

    async def list_community_ids_with_birthday(self, month: int, day: int) -> list[uuid.UUID]:
        """@brief Distinct community ids having an active user born on month/day."""
        stmt = (
            select(User.community_id)
            .where(
                User.deleted_at.is_(None),
                User.is_active.is_(True),
                extract("month", User.birthday) == month,
                extract("day", User.birthday) == day,
            )
            .distinct()
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def list_birthday_users(
        self, community_id: uuid.UUID, month: int, day: int
    ) -> list[tuple[User, str]]:
        """
        @brief Users in a community with a birthday on month/day.
        @return (user, show_birthday_to) pairs; missing settings default to 'community'.
        """
        stmt = (
            select(User, func.coalesce(UserSettings.show_birthday_to, "community"))
            .outerjoin(UserSettings, UserSettings.user_id == User.id)
            .where(
                User.community_id == community_id,
                User.deleted_at.is_(None),
                User.is_active.is_(True),
                extract("month", User.birthday) == month,
                extract("day", User.birthday) == day,
            )
        )
        return [(u, s) for u, s in (await self._session.execute(stmt)).all()]

    async def list_member_ids(self, community_id: uuid.UUID) -> list[uuid.UUID]:
        """@brief Active, non-bot member ids of the community."""
        stmt = select(User.id).where(
            User.community_id == community_id,
            User.deleted_at.is_(None),
            User.is_active.is_(True),
            User.is_bot.is_(False),
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def list_admin_ids(self, community_id: uuid.UUID) -> list[uuid.UUID]:
        """@brief Active admin ids of the community."""
        stmt = select(User.id).where(
            User.community_id == community_id,
            User.deleted_at.is_(None),
            User.is_active.is_(True),
            User.role == "admin",
        )
        return list((await self._session.execute(stmt)).scalars().all())
