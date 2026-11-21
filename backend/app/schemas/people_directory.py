"""
@file people_directory.py
@brief Schemas for GET /api/v1/users/directory.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.home_people import SharedGroup


class DirectoryPerson(BaseModel):
    """@brief One directory entry (privacy flags already applied)."""

    user_id: UUID
    username: str
    display_name: str
    avatar_url: str | None = None
    online: bool = False
    last_seen_at: datetime | None = None
    shared_groups: list[SharedGroup] = []
    primary_group_id: UUID | None = None


class DirectoryResponse(BaseModel):
    """@brief A page of directory entries."""

    items: list[DirectoryPerson]
    next_cursor: str | None = None
