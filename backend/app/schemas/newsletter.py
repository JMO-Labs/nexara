"""
@file newsletter.py
@brief Pydantic schemas for the printable monthly newsletter.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel


class NewsPost(BaseModel):
    """@brief A top post, already trimmed for print."""

    id: uuid.UUID
    author_name: str
    excerpt: str
    created_at: datetime
    reactions: int
    comments: int
    pinned: bool = False
    media_ids: list[uuid.UUID] = []


class NewsPhoto(BaseModel):
    """@brief A photo from a visible post."""

    media_id: uuid.UUID
    post_id: uuid.UUID
    alt: str | None = None


class NewsPerson(BaseModel):
    """@brief A birthday or remembrance."""

    name: str
    date: date
    link: str


class NewsRecipe(BaseModel):
    """@brief A recipe added this month."""

    id: uuid.UUID
    title: str
    author_name: str


class NewsCapsule(BaseModel):
    """@brief A capsule addressed to the viewer that opened this month."""

    id: uuid.UUID
    title: str
    author_name: str


class NewsEvent(BaseModel):
    """@brief An event this month; ``place`` is plain text."""

    id: uuid.UUID
    title: str
    date: date
    place: str | None = None


class Newsletter(BaseModel):
    """@brief One viewer's newsletter for a month."""

    month: str
    community_name: str
    top_posts: list[NewsPost]
    photos: list[NewsPhoto]
    birthdays: list[NewsPerson]
    remembrances: list[NewsPerson]
    new_recipes: list[NewsRecipe]
    opened_capsules: list[NewsCapsule]
    events: list[NewsEvent]
    hidden_posts: list[NewsPost] = []
    """@brief Posts an admin hid (admins only), so they can be restored."""


class OverrideIn(BaseModel):
    """@brief Body for the override endpoint; ``action`` null clears it."""

    post_id: uuid.UUID
    action: Literal["pin", "hide"] | None = None
