"""
@file age_group.py
@brief Schemas for age group suggestions and admin settings.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

AgeGroupValue = Literal["child", "teen", "adult"]


class AgeSuggestionCreate(BaseModel):
    """@brief Member suggestion for another member."""

    subject_id: UUID
    age_group: AgeGroupValue
    note: str | None = Field(None, max_length=500)


class AgeSuggestionResponse(BaseModel):
    """@brief A stored suggestion."""

    id: UUID
    subject_id: UUID
    suggested_by: UUID
    age_group: str
    note: str | None = None
    status: str
    decided_by: UUID | None = None
    decided_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AgeGroupSet(BaseModel):
    """@brief Admin set (null clears) of a user's age group."""

    age_group: AgeGroupValue | None = None


class AgeGroupSettings(BaseModel):
    """@brief Community age settings."""

    adult_requires_approval: bool
