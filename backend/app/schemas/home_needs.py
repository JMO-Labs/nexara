"""
@file home_needs.py
@brief Schemas for GET /home/needs (things that need the viewer's attention).
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class NeedRsvp(BaseModel):
    """@brief An upcoming event the viewer has not responded to."""

    event_id: UUID
    title: str
    starts_at: datetime


class NeedPoll(BaseModel):
    """@brief An open poll the viewer has not voted on."""

    post_id: UUID
    question: str


class NeedPrompt(BaseModel):
    """@brief An active prompt the viewer has not answered."""

    prompt_post_id: UUID
    post_id: UUID
    title: str


class NeedListItems(BaseModel):
    """@brief Count of due list items and the list of the soonest one."""

    count: int
    list_id: UUID
    list_title: str


class HomeNeedsResponse(BaseModel):
    """@brief Aggregate of all needs-you items."""

    rsvps: list[NeedRsvp]
    polls: list[NeedPoll]
    prompt: NeedPrompt | None = None
    list_items: NeedListItems | None = None
