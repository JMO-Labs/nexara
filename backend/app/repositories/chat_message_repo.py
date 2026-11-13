"""
@file chat_message_repo.py
@brief Chat message repository: cursor history, create, edit, tombstone.

``list_with_block_filter`` applies :meth:`BaseRepository.apply_block_filter`
so content from blocked users is hidden from history pages.
"""

from __future__ import annotations

import base64
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatMessage
from app.models.user import User
from app.repositories.base import BaseRepository


TOMBSTONE_CONTENT = "[deleted]"
"""@brief Content placeholder written when a message is soft-deleted."""

DEFAULT_HISTORY_LIMIT = 50
"""@brief Default chat history page size."""

MAX_HISTORY_LIMIT = 100
"""@brief Maximum chat history page size."""


def encode_cursor(created_at: datetime, msg_id: uuid.UUID) -> str:
    """
    @brief Encode a ``(created_at, id)`` pair into an opaque cursor.

    @param created_at Timestamp of the last returned message.
    @param msg_id UUID of the last returned message.
    @return URL-safe base64 string.
    """
    raw = f"{created_at.isoformat()},{msg_id}".encode()
    return base64.urlsafe_b64encode(raw).decode("ascii")


def decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID] | None:
    """
    @brief Decode a cursor back into its ``(created_at, id)`` tuple.

    @param cursor Opaque cursor produced by :func:`encode_cursor`.
    @return ``(datetime, uuid)`` tuple, or None when unparseable.
    """
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii")).decode()
        ts_str, id_str = raw.split(",", 1)
        return datetime.fromisoformat(ts_str), uuid.UUID(id_str)
    except (ValueError, UnicodeDecodeError, TypeError):
        return None


class ChatMessageRepository(BaseRepository[ChatMessage]):
    """
    @brief Async repository for :class:`ChatMessage` operations.

    @param session Async SQLAlchemy session.
    """

    model = ChatMessage

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def create(self, entity: ChatMessage) -> ChatMessage:
        """@brief Persist a prepared ChatMessage and return it hydrated."""
        return await super().create(entity)

    async def create_message(
        self,
        *,
        community_id: uuid.UUID,
        channel_id: uuid.UUID,
        author_id: uuid.UUID,
        content: str,
    ) -> ChatMessage:
        """
        @brief Insert a new ChatMessage row.

        @param community_id Community scope.
        @param channel_id Target channel UUID.
        @param author_id Author UUID.
        @param content Markdown content.
        @return The created ChatMessage with server defaults populated.
        """
        message = ChatMessage(
            community_id=community_id,
            channel_id=channel_id,
            author_id=author_id,
            content=content,
        )
        return await self.create(message)

    async def get(
        self,
        message_id: uuid.UUID,
        community_id: uuid.UUID,
    ) -> ChatMessage | None:
        """
        @brief Fetch a message by ID within a community.

        @param message_id Message UUID.
        @param community_id Community scope.
        @return The message or None.
        """
        stmt = select(ChatMessage).where(
            ChatMessage.id == message_id,
            ChatMessage.community_id == community_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_history_paginated(
        self,
        channel_id: uuid.UUID,
        community_id: uuid.UUID,
        *,
        viewer_id: uuid.UUID | None = None,
        cursor: str | None = None,
        limit: int = DEFAULT_HISTORY_LIMIT,
    ) -> tuple[list[tuple[ChatMessage, User | None]], str | None]:
        """
        @brief Return a paginated slice of channel history (newest first).

        Uses a composite ``(created_at DESC, id DESC)`` cursor to make
        pagination deterministic even when multiple messages share the
        same second.  Applies the block filter when ``viewer_id`` is set.

        @param channel_id Target channel UUID.
        @param community_id Community scope.
        @param viewer_id Requesting user for block filter.
        @param cursor Opaque pagination cursor (see :func:`encode_cursor`).
        @param limit Max rows to return.
        @return Tuple of ``(rows, next_cursor)`` where each row is
                ``(ChatMessage, author_User_or_None)``.
        """
        limit = min(max(limit, 1), MAX_HISTORY_LIMIT)

        stmt = (
            select(ChatMessage, User)
            .outerjoin(User, ChatMessage.author_id == User.id)
            .where(
                ChatMessage.community_id == community_id,
                ChatMessage.channel_id == channel_id,
            )
            .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
        )

        if cursor:
            decoded = decode_cursor(cursor)
            if decoded is not None:
                ts, cid = decoded
                stmt = stmt.where(
                    or_(
                        ChatMessage.created_at < ts,
                        and_(
                            ChatMessage.created_at == ts,
                            ChatMessage.id < cid,
                        ),
                    )
                )

        if viewer_id is not None:
            stmt = self.apply_block_filter(stmt, viewer_id)

        stmt = stmt.limit(limit + 1)
        result = await self._session.execute(stmt)
        rows = list(result.all())

        next_cursor: str | None = None
        if len(rows) > limit:
            rows = rows[:limit]
            last_msg, _ = rows[-1]
            next_cursor = encode_cursor(last_msg.created_at, last_msg.id)

        typed_rows: list[tuple[ChatMessage, User | None]] = [(m, u) for m, u in rows]
        return typed_rows, next_cursor

    async def list_with_block_filter(
        self,
        channel_id: uuid.UUID,
        community_id: uuid.UUID,
        viewer_id: uuid.UUID,
        *,
        limit: int = DEFAULT_HISTORY_LIMIT,
    ) -> list[ChatMessage]:
        """
        @brief Convenience helper: latest messages in a channel with block filter.

        @param channel_id Target channel UUID.
        @param community_id Community scope.
        @param viewer_id Requesting user for block filter.
        @param limit Maximum messages to return.
        @return Plain ChatMessage list, newest first.
        """
        stmt = (
            select(ChatMessage)
            .where(
                ChatMessage.community_id == community_id,
                ChatMessage.channel_id == channel_id,
            )
            .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
            .limit(limit)
        )
        stmt = self.apply_block_filter(stmt, viewer_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update_content(
        self,
        message: ChatMessage,
        content: str,
    ) -> ChatMessage:
        """
        @brief Edit a message's content and stamp ``edited_at``.

        @param message The ChatMessage ORM instance.
        @param content New text content.
        @return The refreshed ChatMessage.
        """
        message.content = content
        message.edited_at = datetime.now(UTC)
        await self._session.flush()
        await self._session.refresh(message)
        return message

    async def soft_delete_message(self, message: ChatMessage) -> ChatMessage:
        """
        @brief Replace the message content with a tombstone marker.

        Keeps the row in place so existing replies / link previews stay
        consistent, and sets ``edited_at`` so clients can render the
        message as "deleted by author/moderator".

        @param message The ChatMessage ORM instance.
        @return The refreshed ChatMessage.
        """
        message.content = TOMBSTONE_CONTENT
        message.edited_at = datetime.now(UTC)
        await self._session.flush()
        await self._session.refresh(message)
        return message

    @staticmethod
    def is_tombstone(message: ChatMessage | dict[str, Any]) -> bool:
        """@brief Return True when the message has been soft-deleted."""
        if isinstance(message, dict):
            return message.get("content") == TOMBSTONE_CONTENT
        return message.content == TOMBSTONE_CONTENT
