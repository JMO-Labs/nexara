"""
@file bookmark.py
@brief Pydantic schemas for post bookmarks.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.post import PostResponse


class BookmarkToggleResponse(BaseModel):
    """@brief Result of toggling a bookmark."""

    post_id: uuid.UUID
    is_bookmarked: bool
    created_at: datetime | None = None


class BookmarkResponse(BaseModel):
    """@brief A bookmarked post."""

    id: uuid.UUID
    post: PostResponse
    bookmarked_at: datetime


class BookmarkList(BaseModel):
    """@brief Paginated bookmarks list."""

    bookmarks: list[BookmarkResponse]
    pagination: dict[str, str | bool | None]
