"""
@file countdown.py
@brief Countdown request/response schemas.
"""

from __future__ import annotations

from datetime import date, time
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class CountdownCreate(BaseModel):
    """@brief Body for creating a countdown."""

    title: str = Field(min_length=1, max_length=120)
    target_date: date
    target_time: time | None = None
    tz: str = "UTC"
    emoji: str | None = Field(default=None, max_length=8)
    cover_media_id: UUID | None = None
    repeat_yearly: bool = False
    visibility: Literal["community", "subgroup", "private"] = "community"
    subgroup_id: UUID | None = None


class CountdownUpdate(BaseModel):
    """@brief Partial update (scope is fixed after creation)."""

    title: str | None = Field(default=None, min_length=1, max_length=120)
    target_date: date | None = None
    target_time: time | None = None
    tz: str | None = None
    emoji: str | None = Field(default=None, max_length=8)
    cover_media_id: UUID | None = None
    repeat_yearly: bool | None = None


class CountdownResponse(BaseModel):
    """@brief A countdown with viewer-relative fields."""

    id: UUID
    author_id: UUID
    title: str
    target_date: date
    target_time: time | None = None
    tz: str
    emoji: str | None = None
    cover_media_id: UUID | None = None
    repeat_yearly: bool
    visibility: str
    subgroup_id: UUID | None = None
    post_id: UUID | None = None
    days_left: int
    next_date: date
    following: bool
    follower_count: int
