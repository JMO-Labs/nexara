"""
@file tag.py
@brief Tag API schemas.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel

from app.schemas.profile import UserSummaryResponse


class TagResponse(BaseModel):
    """@brief One person tagged on a target."""

    id: UUID
    tagged_by: UUID | None = None
    user: UserSummaryResponse


class TagCreate(BaseModel):
    """@brief Tag someone in a photo."""

    user_id: UUID


class TaggedPage(BaseModel):
    """@brief A page of a person's Tagged feed (posts or photos)."""

    kind: Literal["posts", "photos"]
    posts: list[dict[str, Any]] = []
    media_ids: list[UUID] = []
    next_before: datetime | None = None
