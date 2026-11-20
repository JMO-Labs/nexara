"""
@file chat_read_repo.py
@brief Repository for per-user chat read markers and channel unread stats.
"""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import NamedTuple

from sqlalchemy import and_, func, literal, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatMessage
from app.models.chat_read import ChatRead
from app.models.user import User
from app.repositories.base import BaseRepository


class ChannelStat(NamedTuple):
    """
    @brief Per-channel summary for the home chats tile.

    @param last_message Newest visible message, or None.
    @param last_author_name Display name of that message's author.
    @param unread_count Messages by others newer than the read marker.
    @param mentions_me True when any unread message @-mentions the viewer.
    """

    last_message: ChatMessage | None
    last_author_name: str | None
    unread_count: int
    mentions_me: bool


class ChatReadRepository:
    """@brief Read markers (``chat_reads``) and unread/mention statistics."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def mark_read(
        self,
        user_id: uuid.UUID,
        channel_id: uuid.UUID,
        community_id: uuid.UUID,
        at: datetime | None = None,
    ) -> None:
        """
        @brief Upsert the read marker; never moves it backwards.

        @param user_id Reader UUID.
        @param channel_id Channel UUID.
        @param community_id Community scope.
        @param at Marker timestamp (defaults to now).
        """
        ts = at or datetime.now(UTC)
        stmt = pg_insert(ChatRead).values(
            user_id=user_id,
            channel_id=channel_id,
            community_id=community_id,
            last_read_at=ts,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[ChatRead.user_id, ChatRead.channel_id],
            set_={"last_read_at": func.greatest(ChatRead.last_read_at, stmt.excluded.last_read_at)},
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def channel_stats(
        self,
        user_id: uuid.UUID,
        username: str,
        channel_ids: list[uuid.UUID],
        community_id: uuid.UUID,
        since_default: datetime,
    ) -> dict[uuid.UUID, ChannelStat]:
        """
        @brief Compute last message, unread count and mention flag per channel.

        Unread = messages not authored by the viewer newer than the read
        marker (or ``since_default`` when no marker exists).

        @param user_id Viewer UUID.
        @param username Viewer username (for @mention matching).
        @param channel_ids Channels to summarise.
        @param community_id Community scope.
        @param since_default Fallback lower bound when no read row exists.
        @return Mapping channel id -> :class:`ChannelStat` for every requested id.
        """
        result = {cid: ChannelStat(None, None, 0, False) for cid in channel_ids}
        if not channel_ids:
            return result

        last_stmt = (
            select(ChatMessage, User.display_name)
            .outerjoin(User, User.id == ChatMessage.author_id)
            .where(
                ChatMessage.community_id == community_id,
                ChatMessage.channel_id.in_(channel_ids),
            )
            .distinct(ChatMessage.channel_id)
            .order_by(ChatMessage.channel_id, ChatMessage.created_at.desc())
        )
        last_stmt = BaseRepository.apply_block_filter(last_stmt, user_id)
        last = {
            m.channel_id: (m, name) for m, name in (await self._session.execute(last_stmt)).all()
        }

        pattern = func.concat(literal(r"(^|\W)@"), re.escape(username), literal(r"\M"))
        is_mention = ChatMessage.content.op("~*")(pattern)
        unread_stmt = (
            select(
                ChatMessage.channel_id,
                func.count().label("n"),
                func.bool_or(is_mention).label("mention"),
            )
            .outerjoin(
                ChatRead,
                and_(ChatRead.channel_id == ChatMessage.channel_id, ChatRead.user_id == user_id),
            )
            .where(
                ChatMessage.community_id == community_id,
                ChatMessage.channel_id.in_(channel_ids),
                ChatMessage.author_id.is_distinct_from(user_id),
                ChatMessage.created_at > func.coalesce(ChatRead.last_read_at, since_default),
            )
            .group_by(ChatMessage.channel_id)
        )
        unread_stmt = BaseRepository.apply_block_filter(unread_stmt, user_id)
        unread = {
            row.channel_id: (row.n, bool(row.mention))
            for row in (await self._session.execute(unread_stmt)).all()
        }

        for cid in channel_ids:
            msg, name = last.get(cid, (None, None))
            n, mention = unread.get(cid, (0, False))
            result[cid] = ChannelStat(msg, name, n, mention)
        return result
