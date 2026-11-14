"""
@file chat_helpers.py
@brief Chat constants and wire-format helpers.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.models.chat import ChatMessage
from app.models.user import User
from app.repositories.chat_message_repo import TOMBSTONE_CONTENT

CHAT_RATE_LIMIT_PER_MINUTE = 30
"""@brief Maximum messages per user per 60-second window."""

CHAT_PUBSUB_CHANNEL_PREFIX = "chat:"
"""@brief Valkey pub/sub channel prefix for chat broadcasts."""


def channel_pubsub_name(channel_id: uuid.UUID) -> str:
    """@brief Return the Valkey pub/sub channel for a chat channel."""
    return f"{CHAT_PUBSUB_CHANNEL_PREFIX}{channel_id}"


def serialize_message(message: ChatMessage, author: User | None) -> dict[str, Any]:
    """
    @brief Build the wire-format dict for a chat message.

    @param message The ChatMessage ORM instance.
    @param author Optional author User (None when the user was deleted).
    @return Dict ready for JSON serialization.
    """
    is_deleted = message.content == TOMBSTONE_CONTENT
    return {
        "id": str(message.id),
        "channel_id": str(message.channel_id) if message.channel_id else None,
        "author": (
            {
                "id": str(author.id),
                "username": author.username,
                "display_name": author.display_name,
                "avatar_url": author.avatar_url,
            }
            if author is not None
            else None
        ),
        "content": message.content,
        "edited_at": message.edited_at.isoformat() if message.edited_at else None,
        "deleted": is_deleted,
        "created_at": message.created_at.isoformat(),
    }
