"""
@file chat_repo.py
@brief Chat channel + message repositories.

Provides the data-access layer for Phase 2 chat:
  * :class:`ChatChannelRepository` — community / subgroup / direct
    channel lookup and creation.  DMs are resolved via the
    ``direct_message_participants`` join table using a canonical
    (sorted) pair of user UUIDs so the same two users always share the
    same channel row.
  * :class:`ChatMessageRepository` — cursor-paginated history queries,
    message creation, content update (edit) and soft-delete tombstoning.

All reads apply ``community_id`` scoping.  ``list_with_block_filter``
applies :meth:`BaseRepository.apply_block_filter` so content from
users that the viewer blocked (or who blocked the viewer) is hidden
from history pages.
"""

from __future__ import annotations

import base64
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatMessage, DirectMessageParticipant
from app.models.subgroup import ChatChannel
from app.models.user import User
from app.repositories.base import BaseRepository

logger = structlog.get_logger(__name__)

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


class ChatChannelRepository(BaseRepository[ChatChannel]):
    """
    @brief Async repository for :class:`ChatChannel` operations.

    @param session Async SQLAlchemy session.
    """

    model = ChatChannel

    async def get(
        self,
        channel_id: uuid.UUID,
        community_id: uuid.UUID,
    ) -> ChatChannel | None:
        """
        @brief Fetch a channel by ID within a community.

        @param channel_id Channel UUID.
        @param community_id Community scope.
        @return Channel or None.
        """
        stmt = select(ChatChannel).where(
            ChatChannel.id == channel_id,
            ChatChannel.community_id == community_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_community_default(self, community_id: uuid.UUID) -> ChatChannel | None:
        """
        @brief Return the community-wide default channel, if any.

        @param community_id Community scope.
        @return The first ``community``-type channel (by created_at) or None.
        """
        stmt = (
            select(ChatChannel)
            .where(
                ChatChannel.community_id == community_id,
                ChatChannel.channel_type == "community",
            )
            .order_by(ChatChannel.created_at.asc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_for_user(
        self,
        channel_id: uuid.UUID,
        user_id: uuid.UUID,
        community_id: uuid.UUID,
    ) -> ChatChannel | None:
        """
        @brief Fetch a channel only if the given user is permitted to see it.

        Visibility rules:
          * ``community`` channels are visible to any authenticated member.
          * ``subgroup`` channels require a matching subgroup_members row.
          * ``direct`` channels require a row in ``direct_message_participants``.

        @param channel_id Channel UUID.
        @param user_id Requesting user UUID.
        @param community_id Community scope.
        @return Channel or None when the user cannot access it.
        """
        channel = await self.get(channel_id, community_id)
        if channel is None:
            return None

        if channel.channel_type == "community":
            return channel

        if channel.channel_type == "subgroup":
            from app.models.subgroup import SubgroupMember

            sg_stmt = select(SubgroupMember).where(
                SubgroupMember.subgroup_id == channel.subgroup_id,
                SubgroupMember.user_id == user_id,
            )
            sg_result = await self._session.execute(sg_stmt)
            return channel if sg_result.scalar_one_or_none() is not None else None

        if channel.channel_type == "direct":
            dm_stmt = select(DirectMessageParticipant).where(
                DirectMessageParticipant.channel_id == channel.id,
                DirectMessageParticipant.user_id == user_id,
            )
            dm_result = await self._session.execute(dm_stmt)
            return channel if dm_result.scalar_one_or_none() is not None else None

        return None

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        community_id: uuid.UUID,
    ) -> list[ChatChannel]:
        """
        @brief Return every channel the user can see (community, subgroup, direct).

        @param user_id User UUID.
        @param community_id Community scope.
        @return List of channels ordered by channel_type, created_at ASC.
        """
        from app.models.subgroup import SubgroupMember

        subgroup_member_ids = select(SubgroupMember.subgroup_id).where(
            SubgroupMember.user_id == user_id,
        )
        dm_channel_ids = select(DirectMessageParticipant.channel_id).where(
            DirectMessageParticipant.user_id == user_id,
        )

        stmt = (
            select(ChatChannel)
            .where(
                ChatChannel.community_id == community_id,
                or_(
                    ChatChannel.channel_type == "community",
                    and_(
                        ChatChannel.channel_type == "subgroup",
                        ChatChannel.subgroup_id.in_(subgroup_member_ids),
                    ),
                    and_(
                        ChatChannel.channel_type == "direct",
                        ChatChannel.id.in_(dm_channel_ids),
                    ),
                ),
            )
            .order_by(ChatChannel.channel_type.asc(), ChatChannel.created_at.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_dm_threads(
        self,
        user_id: uuid.UUID,
        community_id: uuid.UUID,
    ) -> list[tuple[ChatChannel, User]]:
        """
        @brief List every DM thread the user participates in.

        Pairs each DM channel with the *other* participant's user row.

        @param user_id Requesting user UUID.
        @param community_id Community scope.
        @return List of ``(ChatChannel, peer_User)`` tuples newest first.
        """
        my_dm_ids = select(DirectMessageParticipant.channel_id).where(
            DirectMessageParticipant.user_id == user_id,
        )
        stmt = (
            select(ChatChannel, User)
            .join(
                DirectMessageParticipant,
                DirectMessageParticipant.channel_id == ChatChannel.id,
            )
            .join(User, User.id == DirectMessageParticipant.user_id)
            .where(
                ChatChannel.community_id == community_id,
                ChatChannel.channel_type == "direct",
                ChatChannel.id.in_(my_dm_ids),
                DirectMessageParticipant.user_id != user_id,
            )
            .order_by(ChatChannel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return [(c, u) for c, u in result.all()]

    async def get_or_create_dm(
        self,
        user_a: uuid.UUID,
        user_b: uuid.UUID,
        community_id: uuid.UUID,
    ) -> tuple[ChatChannel, bool]:
        """
        @brief Return the DM channel shared by two users, creating it if absent.

        The canonical DM for a pair is determined by intersecting the
        ``direct_message_participants`` rows for both users: a channel
        shared by both is the existing thread, otherwise a new
        ``direct`` channel plus two participant rows are inserted.

        @param user_a First participant UUID.
        @param user_b Second participant UUID.
        @param community_id Community scope.
        @return ``(channel, created)`` tuple.
        """
        if user_a == user_b:
            raise ValueError("Cannot create DM with yourself")

        a_channels = select(DirectMessageParticipant.channel_id).where(
            DirectMessageParticipant.user_id == user_a,
        )
        b_channels = select(DirectMessageParticipant.channel_id).where(
            DirectMessageParticipant.user_id == user_b,
        )
        stmt = (
            select(ChatChannel)
            .where(
                ChatChannel.community_id == community_id,
                ChatChannel.channel_type == "direct",
                ChatChannel.id.in_(a_channels),
                ChatChannel.id.in_(b_channels),
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing is not None:
            return (existing, False)

        # Build a deterministic name ``dm:{sorted_a}:{sorted_b}``.
        sorted_pair = sorted([user_a, user_b])
        channel = ChatChannel(
            community_id=community_id,
            name=f"dm:{sorted_pair[0]}:{sorted_pair[1]}",
            channel_type="direct",
            subgroup_id=None,
        )
        self._session.add(channel)
        await self._session.flush()
        await self._session.refresh(channel)

        self._session.add_all(
            [
                DirectMessageParticipant(channel_id=channel.id, user_id=user_a),
                DirectMessageParticipant(channel_id=channel.id, user_id=user_b),
            ]
        )
        await self._session.flush()
        return (channel, True)


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
