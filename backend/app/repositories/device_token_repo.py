"""
@file device_token_repo.py
@brief Repository for native push device tokens.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select

from app.models.device_token import DeviceToken
from app.repositories.base import BaseRepository


class DeviceTokenRepo(BaseRepository[DeviceToken]):
    """@brief Async repository for :class:`DeviceToken` (community scoped, soft delete)."""

    model = DeviceToken

    async def find_by_token(self, token: str) -> DeviceToken | None:
        """
        @brief Find a token row in any state (token is globally unique).

        Intentionally ignores ``deleted_at``/community so an upsert can revive
        or reassign the row without violating the unique constraint.

        @param token Device token string.
        @return The row or None.
        """
        result = await self._session.execute(select(DeviceToken).where(DeviceToken.token == token))
        return result.scalar_one_or_none()

    async def find_active(
        self, community_id: uuid.UUID, user_id: uuid.UUID, token: str
    ) -> DeviceToken | None:
        """
        @brief Find a live token owned by the user within the community.

        @param community_id Community scope.
        @param user_id Owner UUID.
        @param token Device token string.
        @return The row or None.
        """
        stmt = self._base_query().where(
            DeviceToken.community_id == community_id,
            DeviceToken.user_id == user_id,
            DeviceToken.token == token,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def reassign(
        self,
        device: DeviceToken,
        *,
        user_id: uuid.UUID,
        community_id: uuid.UUID,
        platform: str,
    ) -> DeviceToken:
        """
        @brief Point an existing token at a user/community and revive it.

        @return The updated row.
        """
        device.user_id = user_id
        device.community_id = community_id
        device.platform = platform
        device.deleted_at = None
        await self._session.flush()
        await self._session.refresh(device)
        return device
