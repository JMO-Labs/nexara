"""
@file digest_repo.py
@brief Data access for the notification digest queue.
"""

from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification_digest import NotificationDigestQueue as Q


class DigestRepository:
    """@brief Enqueue, drain and list pending digest rows."""

    def __init__(self, session: AsyncSession) -> None:
        """@param session Request/task-scoped async session."""
        self._session = session

    async def enqueue(self, user_id: uuid.UUID, type_key: str, notification_id: uuid.UUID) -> Q:
        """@brief Queue a notification for digest. @return The inserted row."""
        row = Q(user_id=user_id, type_key=type_key, notification_id=notification_id)
        self._session.add(row)
        await self._session.flush()
        return row

    async def drain(self, user_id: uuid.UUID, type_key: str) -> list[uuid.UUID]:
        """@brief Atomically delete and return queued notification ids (idempotent)."""
        stmt = (
            delete(Q)
            .where(Q.user_id == user_id, Q.type_key == type_key)
            .returning(Q.notification_id)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def list_users_with_pending(self) -> list[uuid.UUID]:
        """@brief Distinct user ids that have queued rows."""
        res = await self._session.execute(select(Q.user_id).distinct())
        return list(res.scalars().all())

    async def list_pending_types(self, user_id: uuid.UUID) -> list[str]:
        """@brief Distinct type keys queued for a user."""
        res = await self._session.execute(select(Q.type_key).where(Q.user_id == user_id).distinct())
        return list(res.scalars().all())
