"""
@file chat_context.py
@brief Schemas for GET /api/v1/chat/channels/{id}/context (details panel).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ContextPeer(BaseModel):
    """@brief DM peer card; privacy-gated fields are null when not shared."""

    id: UUID
    display_name: str
    username: str
    avatar_url: str | None = None
    last_seen_at: datetime | None = None
    local_time_tz: str | None = None
    birthday_in_days: int | None = None


class ContextGroup(BaseModel):
    """@brief Subgroup the viewer and peer share."""

    id: UUID
    name: str
    slug: str


class ContextEvent(BaseModel):
    """@brief Upcoming event summary."""

    id: UUID
    title: str
    starts_at: datetime


class ContextMember(BaseModel):
    """@brief Group member summary."""

    id: UUID
    display_name: str
    avatar_url: str | None = None


class ContextList(BaseModel):
    """@brief Open list summary."""

    id: UUID
    title: str
    item_count: int


class DmContext(BaseModel):
    """@brief Details for a direct conversation."""

    kind: Literal["dm"] = "dm"
    peer: ContextPeer
    shared_groups: list[ContextGroup] = Field(default_factory=list)
    upcoming_events: list[ContextEvent] = Field(default_factory=list)


class GroupContext(BaseModel):
    """@brief Details for a community or subgroup channel."""

    kind: Literal["group"] = "group"
    members: list[ContextMember] = Field(default_factory=list)
    member_count: int = 0
    next_event: ContextEvent | None = None
    open_lists: list[ContextList] = Field(default_factory=list)
