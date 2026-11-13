"""
@file settings_repo.py
@brief Repository for per-user settings (UPSERT pattern).

The settings row is created with defaults on user registration.
``get_or_create()`` ensures a row always exists before reads.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_settings import UserSettings


class SettingsRepository:
    """
    @brief Async repository for user settings.

    Does not extend BaseRepository because UserSettings uses ``user_id``
    as the primary key, not a UUID ``id`` column.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_user_id(self, user_id: uuid.UUID) -> UserSettings | None:
        """
        @brief Fetch settings for a user by user_id.

        @param user_id UUID of the user.
        @return The UserSettings instance or None if not found.
        """
        stmt = select(UserSettings).where(UserSettings.user_id == user_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create(
        self,
        user_id: uuid.UUID,
        community_id: uuid.UUID,
    ) -> UserSettings:
        """
        @brief Fetch settings for a user, creating with defaults if missing.

        @param user_id UUID of the user.
        @param community_id Community scope.
        @return The UserSettings instance.
        """
        stmt = select(UserSettings).where(UserSettings.user_id == user_id)
        result = await self._session.execute(stmt)
        settings = result.scalar_one_or_none()

        if settings is not None:
            return settings

        settings = UserSettings(user_id=user_id, community_id=community_id)
        self._session.add(settings)
        await self._session.flush()
        await self._session.refresh(settings)
        return settings

    async def update(
        self,
        user_id: uuid.UUID,
        data: dict[str, Any],
    ) -> UserSettings:
        """
        @brief Apply partial updates to a user's settings.

        @param user_id UUID of the user.
        @param data Dict of setting fields to update.
        @return The updated UserSettings instance.
        """
        stmt = select(UserSettings).where(UserSettings.user_id == user_id)
        result = await self._session.execute(stmt)
        settings = result.scalar_one_or_none()

        if settings is None:
            msg = f"Settings not found for user {user_id}"
            raise ValueError(msg)

        for key, value in data.items():
            if hasattr(settings, key):
                setattr(settings, key, value)

        await self._session.flush()
        await self._session.refresh(settings)
        return settings

    async def count_sassybot_opt_outs(self, community_id: uuid.UUID) -> int:
        """
        @brief Number of members in a community who disabled Sassybot.

        @param community_id Community scope.
        @return Count of settings rows with ``allow_sassybot`` false.
        """
        stmt = (
            select(func.count())
            .select_from(UserSettings)
            .where(
                UserSettings.community_id == community_id,
                UserSettings.allow_sassybot.is_(False),
            )
        )
        return int((await self._session.execute(stmt)).scalar_one())
