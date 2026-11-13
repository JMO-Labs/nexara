"""
@file notification_repo.py
@brief Repository for in-app notifications.

Provides create, list, mark-read, and cleanup operations.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
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
        *,
        types: list[str] | None = None,
        unread_only: bool = False,
    ) -> tuple[list[Notification], str | None]:
        """
        @brief List notifications for a user with cursor pagination.

        @param user_id Recipient user UUID.
        @param cursor Opaque cursor from previous page.
        @param limit Max items per page.
        @param types Restrict to these type keys (None = all).
        @param unread_only Only rows with read_at NULL.
        @return Tuple of (items, next_cursor).
        """
        stmt = select(Notification).where(Notification.user_id == user_id)
        if types is not None:
            stmt = stmt.where(Notification.type.in_(types))
        if unread_only:
            stmt = stmt.where(Notification.read_at.is_(None))
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

    async def list_active(self, user_id: uuid.UUID, limit: int = 20) -> list[Notification]:
        """
        @brief List a user's non-dismissed notifications, newest first.

        @param user_id Recipient user UUID.
        @param limit Max rows.
        @return Active notifications.
        """
        stmt = (
            select(Notification)
            .where(Notification.user_id == user_id, Notification.dismissed_at.is_(None))
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def dismiss(self, user_id: uuid.UUID, notification_id: uuid.UUID) -> None:
        """
        @brief Dismiss one notification owned by the user.

        @param user_id Owner UUID.
        @param notification_id Notification UUID.
        @throws NotFoundError If missing or not owned by user_id.
        """
        stmt = select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
        result = await self._session.execute(stmt)
        notification = result.scalar_one_or_none()
        if notification is None:
            raise NotFoundError("Notification not found")
        notification.dismissed_at = datetime.now(UTC)
        await self._session.flush()

    async def dismiss_all(self, user_id: uuid.UUID) -> int:
        """
        @brief Dismiss all of a user's active notifications.

        @param user_id Owner UUID.
        @return Number of rows dismissed.
        """
        stmt = (
            update(Notification)
            .where(Notification.user_id == user_id, Notification.dismissed_at.is_(None))
            .values(dismissed_at=datetime.now(UTC))
        )
        result = await self._session.execute(stmt)
        return cast(int, getattr(result, "rowcount", 0)) or 0

    async def upsert_grouped(
        self,
        user_id: uuid.UUID,
        type: str,
        payload: dict[str, Any],
        community_id: uuid.UUID,
        group_key: str | None = None,
        actor_id: uuid.UUID | None = None,
    ) -> Notification:
        """
        @brief Insert a notification (stub; windowed merge lands in #81).

        @param user_id Recipient user UUID.
        @param type Notification type.
        @param payload JSON payload.
        @param community_id Community scope.
        @param group_key Grouping key; currently stored, no merge performed.
        @param actor_id Optional actor, recorded in actor_ids.
        @return The persisted Notification.
        """
        notification = Notification(
            user_id=user_id,
            community_id=community_id,
            type=type,
            payload=payload,
            group_key=group_key,
            count=1,
            actor_ids=[actor_id] if actor_id else [],
        )
        self._session.add(notification)
        await self._session.flush()
        await self._session.refresh(notification)
        return notification

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

    async def unread_counts_by_type(self, user_id: uuid.UUID) -> dict[str, int]:
        """
        @brief Count unread notifications per type for a user.

        @param user_id Recipient user UUID.
        @return {type_key: unread_count} (non-zero only).
        """
        stmt = (
            select(Notification.type, func.count())
            .where(Notification.user_id == user_id, Notification.read_at.is_(None))
            .group_by(Notification.type)
        )
        result = await self._session.execute(stmt)
        return {str(t): int(c) for t, c in result.all()}

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

    async def mark_all_read(self, user_id: uuid.UUID, *, types: list[str] | None = None) -> int:
        """
        @brief Mark all unread notifications as read for a user.

        @param user_id Recipient user UUID.
        @param types Restrict to these type keys (None = all).
        @return Number of notifications updated.
        """
        stmt = (
            select(Notification)
            .where(Notification.user_id == user_id)
            .where(Notification.read_at.is_(None))
        )
        if types is not None:
            stmt = stmt.where(Notification.type.in_(types))
        result = await self._session.execute(stmt)
        notifications = result.scalars().all()
        now = datetime.now(UTC)
        for n in notifications:
            n.read_at = now
        await self._session.flush()
        return len(notifications)

    async def delete_all_for_user(
        self,
        user_id: uuid.UUID,
        *,
        types: list[str] | None = None,
        before: datetime | None = None,
    ) -> int:
        """
        @brief Delete a user's notifications, optionally filtered.

        @param user_id Recipient user UUID.
        @param types Restrict to these type keys (None = all).
        @param before Only rows created strictly before this instant.
        @return Number of rows deleted.
        """
        stmt = delete(Notification).where(Notification.user_id == user_id)
        if types is not None:
            stmt = stmt.where(Notification.type.in_(types))
        if before is not None:
            stmt = stmt.where(Notification.created_at < before)
        result = await self._session.execute(stmt)
        return cast(int, getattr(result, "rowcount", 0)) or 0

    async def delete_one(self, user_id: uuid.UUID, notification_id: uuid.UUID) -> bool:
        """
        @brief Delete one notification owned by the user.

        @param user_id Owner UUID.
        @param notification_id Notification UUID.
        @return True if a row was deleted, False if missing or not owned.
        """
        stmt = delete(Notification).where(
            Notification.id == notification_id, Notification.user_id == user_id
        )
        result = await self._session.execute(stmt)
        return bool(cast(int, getattr(result, "rowcount", 0)))

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
