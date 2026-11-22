"""
@file tag.py
@brief Tag API schemas.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, model_validator

from app.schemas.profile import UserSummaryResponse


class HouseholdRef(BaseModel):
    """@brief Tagged household member or pet."""

    id: UUID
    name: str
    kind: Literal["person", "pet"]
    photo_media_id: UUID | None = None


class TagResponse(BaseModel):
    """@brief One person (member or household) tagged on a target."""

    id: UUID
    tagged_by: UUID | None = None
    user: UserSummaryResponse | None = None
    household: HouseholdRef | None = None


class TagCreate(BaseModel):
    """@brief Tag a member (user_id) or household member/pet (household_id) in a photo."""

    user_id: UUID | None = None
    household_id: UUID | None = None

    @model_validator(mode="after")
    def _one(self) -> TagCreate:
        if (self.user_id is None) == (self.household_id is None):
            raise ValueError("Give exactly one of user_id or household_id")
        return self


class TaggedPage(BaseModel):
    """@brief A page of a person's Tagged feed (posts or photos)."""

    kind: Literal["posts", "photos"]
    posts: list[dict[str, Any]] = []
    media_ids: list[UUID] = []
    next_before: datetime | None = None
