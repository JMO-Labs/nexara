"""
@file home_chats.py
@brief Schemas for GET /api/v1/home/chats.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class HomeChatPeer(BaseModel):
    """@brief The other participant of a direct thread."""

    id: UUID
    display_name: str
    avatar_url: str | None = None


class HomeChatMessage(BaseModel):
    """@brief Preview of a thread's newest message (content <= 140 chars)."""

    id: UUID
    author_name: str | None = None
    content: str
    created_at: datetime


class HomeChatThread(BaseModel):
    """@brief One ranked chat thread for the home tile."""

    channel_id: UUID
    name: str
    channel_type: Literal["community", "subgroup", "direct"]
    subgroup_id: UUID | None = None
    peer: HomeChatPeer | None = None
    last_message: HomeChatMessage | None = None
    unread_count: int
    mentions_me: bool
    last_activity_at: datetime


class HomeChatsResponse(BaseModel):
    """@brief Response envelope for the home chats endpoint."""

    items: list[HomeChatThread]
