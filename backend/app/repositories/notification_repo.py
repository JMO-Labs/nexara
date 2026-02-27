"""
@file notification_repo.py
@brief Repository for in-app notifications.

Provides create, list, mark-read, and cleanup operations.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.repositories.base import BaseRepository


class NotificationRepository(BaseRepository[Notification]):
    """
    @brief Async repository for :class:`Notification` entities.

    Notifications are scoped by user_id for listing and mark-read.
    """

    model = Notification

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def create(  # type: ignore[override]
        self,
        user_id: uuid.UUID,
        type: str,
        payload: dict[str, Any],
        community_id: uuid.UUID,
    ) -> Notification:
        """
        @brief Create a new notification.

        @param user_id Recipient user UUID.
        @param type Notification type (mention, comment, etc.).
        @param payload JSON payload (message, link, actor_id, etc.).
        @param community_id Community scope.
        @return The persisted Notification instance.
        """
        notification = Notification(
            user_id=user_id,
            community_id=community_id,
            type=type,
            payload=payload,
        )
        self._session.add(notification)
        await self._session.flush()
        await self._session.refresh(notification)
        return notification

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        cursor: str | None = None,
        limit: int = 20,
    ) -> tuple[list[Notification], str | None]:
        """
        @brief List notifications for a user with cursor pagination.

        @param user_id Recipient user UUID.
        @param cursor Opaque cursor from previous page.
        @param limit Max items per page.
        @return Tuple of (items, next_cursor).
        """
        stmt = select(Notification).where(Notification.user_id == user_id)
        stmt = stmt.order_by(Notification.created_at.desc())

        if cursor:
            try:
                cursor_id = uuid.UUID(cursor)
                stmt = stmt.where(Notification.id < cursor_id)
            except ValueError:
                pass

        stmt = stmt.limit(limit + 1)
        result = await self._session.execute(stmt)
        rows = list(result.scalars().all())

        next_cursor: str | None = None
        if len(rows) > limit:
            rows = rows[:limit]
            next_cursor = str(rows[-1].id)

        return rows, next_cursor

    async def get_unread_count(self, user_id: uuid.UUID) -> int:
        """
        @brief Count unread notifications for a user.

        @param user_id Recipient user UUID.
        @return Unread count.
        """
        stmt = (
            select(func.count())
            .select_from(Notification)
            .where(Notification.user_id == user_id)
            .where(Notification.read_at.is_(None))
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def mark_read(self, notification_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """
        @brief Mark a single notification as read.

        @param notification_id Notification UUID.
        @param user_id Recipient (ensures ownership).
        @return True if updated, False if not found.
        """
        stmt = select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
        result = await self._session.execute(stmt)
        notification = result.scalar_one_or_none()
        if notification is None:
            return False
        notification.read_at = datetime.now(UTC)
        await self._session.flush()
        return True

    async def mark_all_read(self, user_id: uuid.UUID) -> int:
        """
        @brief Mark all unread notifications as read for a user.

        @param user_id Recipient user UUID.
        @return Number of notifications updated.
        """
        stmt = (
            select(Notification)
            .where(Notification.user_id == user_id)
            .where(Notification.read_at.is_(None))
        )
        result = await self._session.execute(stmt)
        notifications = result.scalars().all()
        now = datetime.now(UTC)
        for n in notifications:
            n.read_at = now
        await self._session.flush()
        return len(notifications)

    async def delete_old(self, days: int) -> int:
        """
        @brief Delete notifications older than the given number of days.

        @param days Age threshold in days.
        @return Number of rows deleted.
        """
        cutoff = datetime.now(UTC) - timedelta(days=days)
        stmt = delete(Notification).where(Notification.created_at < cutoff)
        result = await self._session.execute(stmt)
        return cast(int, getattr(result, "rowcount", 0)) or 0
