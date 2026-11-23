"""
@file story.py
@brief Pydantic schemas for story requests and the profile Stories tab.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class StoryAsk(BaseModel):
    """@brief Body for asking a member to tell a story."""

    teller_id: uuid.UUID
    question: str = Field(min_length=1, max_length=280)


class StoryAnswer(BaseModel):
    """@brief Body linking the teller's own post as the answer."""

    post_id: uuid.UUID


class StoryPerson(BaseModel):
    """@brief Minimal person reference."""

    id: uuid.UUID
    display_name: str


class StoryRequestOut(BaseModel):
    """@brief A request as one party sees it (asker never sees ``declined``)."""

    id: uuid.UUID
    asker: StoryPerson
    teller: StoryPerson
    question: str
    status: Literal["open", "answered", "declined", "expired"]
    post_id: uuid.UUID | None = None
    created_at: datetime
    expires_at: datetime


class StoryRequestList(BaseModel):
    """@brief ``incoming`` = open asks for me; ``outgoing`` = asks I made."""

    incoming: list[StoryRequestOut]
    outgoing: list[StoryRequestOut]


class StoryItem(BaseModel):
    """@brief One Stories-tab entry: a visible post and the question it answers."""

    question: str | None = None
    post: dict[str, Any]


class StoryList(BaseModel):
    """@brief Page of stories, newest first."""

    items: list[StoryItem]
    next_cursor: str | None = None
