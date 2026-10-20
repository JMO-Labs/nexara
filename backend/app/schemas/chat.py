"""
@file chat.py
@brief Pydantic schemas for the chat subsystem.

Defines request/response shapes used by the chat REST API and the
WebSocket chat handler.  Message history pages are cursor-paginated via
an opaque base64-encoded ``(created_at_iso, id)`` descending cursor.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ChatAuthorResponse(BaseModel):
    """@brief Author summary embedded inside chat message responses."""

    id: UUID
    username: str
    display_name: str
    avatar_url: str | None = None

    model_config = {"from_attributes": True}


class ChatMessageCreate(BaseModel):
    """
    @brief Payload for sending a new chat message.

    @param channel_id Target :class:`ChatChannel` UUID.
    @param content Markdown content (1-5000 characters).
    """

    channel_id: UUID
    content: str = Field(..., min_length=1, max_length=5000)


class ChatMessageUpdate(BaseModel):
    """
    @brief Payload for editing an existing message.

    @param content New markdown content (1-5000 characters).
    """

    content: str = Field(..., min_length=1, max_length=5000)


class ChatMessageResponse(BaseModel):
    """
    @brief Single chat message payload for HTTP and WS responses.

    @param id Message UUID.
    @param channel_id ID of the channel the message belongs to.
    @param author Author summary (may be ``None`` for deleted users).
    @param content Message text (``"[deleted]"`` after soft-delete).
    @param edited_at Non-null when the message has been edited.
    @param deleted True when the message is a tombstone.
    @param created_at Creation timestamp.
    """

    id: UUID
    channel_id: UUID
    author: ChatAuthorResponse | None = None
    content: str
    edited_at: datetime | None = None
    deleted: bool = False
    created_at: datetime


class ChannelResponse(BaseModel):
    """
    @brief Summary of a chat channel visible to the user.

    @param id Channel UUID.
    @param name Display name (for DMs this is the peer's display name).
    @param channel_type One of ``community``, ``subgroup``, ``direct``.
    @param subgroup_id Populated for subgroup channels.
    @param created_at Creation timestamp.
    """

    id: UUID
    name: str
    channel_type: str
    subgroup_id: UUID | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DirectMessageThreadResponse(BaseModel):
    """
    @brief Summary of a direct-message conversation.

    @param channel_id Underlying :class:`ChatChannel` UUID.
    @param peer Summary of the other participant.
    @param created_at When the thread was established.
    """

    channel_id: UUID
    peer: ChatAuthorResponse
    created_at: datetime


class MessageHistoryResponse(BaseModel):
    """
    @brief Paginated chat history page.

    @param items Messages ordered newest-first.
    @param cursor Opaque next-page cursor (base64 of ``created_at,id``).
    @param has_more True when more pages remain.
    """

    items: list[ChatMessageResponse] = Field(default_factory=list)
    cursor: str | None = None
    has_more: bool = False
