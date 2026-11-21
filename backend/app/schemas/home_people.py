"""
@file home_people.py
@brief Schemas for GET /api/v1/home/people.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class SharedGroup(BaseModel):
    """@brief A subgroup shared between the viewer and a person."""

    id: UUID
    name: str
    accent_color: str | None = None


class HomePerson(BaseModel):
    """@brief One entry in the home people strip (privacy flags already applied)."""

    user_id: UUID
    username: str
    display_name: str
    avatar_url: str | None = None
    online: bool = False
    birthday_in_days: int | None = None
    last_seen_at: datetime | None = None
    shared_groups: list[SharedGroup] = []
    primary_group_id: UUID | None = None
    shared_events_30d: int = 0
    favorite: bool = False


class HomePeopleResponse(BaseModel):
    """@brief People strip payload."""

    items: list[HomePerson]


class FavoritesResponse(BaseModel):
    """@brief The viewer's pinned people, in pin order."""

    favorites: list[UUID]
