"""
@file push_repo.py
@brief Repository for Web Push subscriptions.
"""

from __future__ import annotations

import uuid
from typing import Any, cast

from sqlalchemy import delete, select
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import PushSubscription
from app.repositories.base import BaseRepository


class PushSubscriptionRepository(BaseRepository[PushSubscription]):
    """
    @brief Async repository for :class:`PushSubscription` entities.

    Push subscriptions are keyed by endpoint (unique) and user_id.
    """

    model = PushSubscription

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def find_by_endpoint(self, endpoint: str) -> PushSubscription | None:
        """
        @brief Find a subscription by its push endpoint URL.

        @param endpoint Web Push endpoint URL.
        @return The subscription or None.
        """
        stmt = select(PushSubscription).where(PushSubscription.endpoint == endpoint)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: uuid.UUID) -> list[PushSubscription]:
        """
        @brief List all push subscriptions for a user.

        @param user_id User UUID.
        @return List of subscriptions.
        """
        stmt = select(PushSubscription).where(PushSubscription.user_id == user_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def delete_by_endpoint(self, endpoint: str) -> bool:
        """
        @brief Delete a subscription by endpoint.

        @param endpoint Web Push endpoint URL.
        @return True if a row was deleted, False otherwise.
        """
        stmt = delete(PushSubscription).where(PushSubscription.endpoint == endpoint)
        result = await self._session.execute(stmt)
        rowcount = cast(CursorResult[Any], result).rowcount or 0
        return rowcount > 0

    async def cleanup_stale(self, endpoint: str) -> None:
        """
        @brief Delete a subscription (e.g. after 410 Gone from push service).

        @param endpoint Web Push endpoint URL.
        """
        await self.delete_by_endpoint(endpoint)
