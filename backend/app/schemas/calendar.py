"""
@file calendar.py
@brief Pydantic schemas for the Calendar entity.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

CalendarKind = Literal["personal", "community", "subgroup"]


class CalendarResponse(BaseModel):
    """@brief Calendar visible to a user (one of personal/community/subgroup)."""

    id: UUID
    kind: CalendarKind
    name: str
    color: str | None = None
    owner_id: UUID | None = None
    subgroup_id: UUID | None = None
    external_provider: str | None = None
    external_id: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CalendarUpdate(BaseModel):
    """@brief Partial update for a calendar (rename / recolor)."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
