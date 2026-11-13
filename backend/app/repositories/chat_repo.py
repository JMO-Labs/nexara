"""
@file chat_repo.py
@brief Chat channel + message repositories.

Facade re-exporting the split modules
(``chat_channel_repo`` and ``chat_message_repo``).

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

from app.repositories.chat_channel_repo import ChatChannelRepository
from app.repositories.chat_message_repo import (
    DEFAULT_HISTORY_LIMIT,
    MAX_HISTORY_LIMIT,
    TOMBSTONE_CONTENT,
    ChatMessageRepository,
    decode_cursor,
    encode_cursor,
)

__all__ = [
    "DEFAULT_HISTORY_LIMIT",
    "MAX_HISTORY_LIMIT",
    "TOMBSTONE_CONTENT",
    "ChatChannelRepository",
    "ChatMessageRepository",
    "decode_cursor",
    "encode_cursor",
]
