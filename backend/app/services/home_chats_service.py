"""
@file home_chats_service.py
@brief Ranks the viewer's chat threads for the home tile.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from app.models.user import User
from app.repositories.chat_channel_repo import ChatChannelRepository
from app.repositories.chat_read_repo import ChatReadRepository
from app.schemas.home_chats import (
    HomeChatMessage,
    HomeChatPeer,
    HomeChatsResponse,
    HomeChatThread,
)

PREVIEW_MAX = 140
UNREAD_WINDOW = timedelta(days=7)


def _truncate(text: str) -> str:
    """@brief Cut text to PREVIEW_MAX chars, ending with an ellipsis."""
    return text if len(text) <= PREVIEW_MAX else text[: PREVIEW_MAX - 1] + "…"


class HomeChatsService:
    """@brief Builds the ranked home chat thread list."""

    def __init__(
        self,
        channel_repo: ChatChannelRepository,
        read_repo: ChatReadRepository,
        community_id: uuid.UUID,
    ) -> None:
        self._channels = channel_repo
        self._reads = read_repo
        self._community_id = community_id

    async def list(self, user: User, limit: int) -> HomeChatsResponse:
        """
        @brief Return up to ``limit`` threads ranked mentions, unread, recency.

        @param user Viewer.
        @param limit Max threads to return.
        @return HomeChatsResponse.
        """
        channels = await self._channels.list_for_user(user.id, self._community_id)
        peers = {
            c.id: p for c, p in await self._channels.list_dm_threads(user.id, self._community_id)
        }
        since = datetime.now(UTC) - UNREAD_WINDOW
        stats = await self._reads.channel_stats(
            user.id, user.username, [c.id for c in channels], self._community_id, since
        )

        threads: list[HomeChatThread] = []
        for c in channels:
            if c.channel_type == "direct" and c.id not in peers:
                continue
            st = stats[c.id]
            peer = peers.get(c.id)
            msg = st.last_message
            threads.append(
                HomeChatThread(
                    channel_id=c.id,
                    name=peer.display_name if peer is not None else c.name,
                    channel_type=c.channel_type,
                    subgroup_id=c.subgroup_id,
                    peer=(
                        HomeChatPeer(
                            id=peer.id, display_name=peer.display_name, avatar_url=peer.avatar_url
                        )
                        if peer is not None
                        else None
                    ),
                    last_message=(
                        HomeChatMessage(
                            id=msg.id,
                            author_name=st.last_author_name,
                            content=_truncate(msg.content),
                            created_at=msg.created_at,
                        )
                        if msg is not None
                        else None
                    ),
                    unread_count=st.unread_count,
                    mentions_me=st.mentions_me,
                    last_activity_at=msg.created_at if msg is not None else c.created_at,
                )
            )
        threads.sort(
            key=lambda t: (
                not t.mentions_me,
                t.unread_count == 0,
                -t.last_activity_at.timestamp(),
            )
        )
        return HomeChatsResponse(items=threads[:limit])
