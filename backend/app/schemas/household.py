"""
@file household.py
@brief Household member / pet API schemas.
"""

from __future__ import annotations

from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

Level = Literal["private", "groups", "community"]
Kind = Literal["person", "pet"]


def _clean_list(v: list[str] | None) -> list[str] | None:
    """@brief Trim, drop blanks and duplicates, cap at 20 items of 60 chars."""
    if v is None:
        return None
    out: list[str] = []
    for item in v:
        t = item.strip()[:60]
        if t and t not in out:
            out.append(t)
    return out[:20]


class HouseholdUpdate(BaseModel):
    """@brief Editable fields; omitted fields are unchanged."""

    name: str | None = Field(None, min_length=1, max_length=80)
    relation: str | None = Field(None, max_length=60)
    birthday: date | None = None
    show_birth_year: bool | None = None
    photo_media_id: UUID | None = None
    visibility: Level | None = None
    bio: str | None = Field(None, max_length=1000)
    species: str | None = Field(None, max_length=40)
    breed: str | None = Field(None, max_length=60)
    gotcha_day: date | None = None
    likes: list[str] | None = None
    dislikes: list[str] | None = None
    care_card: str | None = Field(None, max_length=4000)
    care_visibility: Level | None = None

    _lists = field_validator("likes", "dislikes")(_clean_list)


class HouseholdCreate(HouseholdUpdate):
    """@brief New member: kind and name required."""

    kind: Kind
    name: str = Field(..., min_length=1, max_length=80)


class HouseholdResponse(BaseModel):
    """@brief A member as the viewer may see it."""

    id: UUID
    owner_id: UUID
    kind: Kind
    name: str
    relation: str | None = None
    birthday: str | None = None
    show_birth_year: bool = False
    photo_media_id: UUID | None = None
    visibility: Level
    bio: str | None = None
    species: str | None = None
    breed: str | None = None
    gotcha_day: date | None = None
    likes: list[str] = []
    dislikes: list[str] = []
    care_card: str | None = None
    care_visibility: Level
    can_edit: bool = False


class Celebration(BaseModel):
    """@brief Upcoming birthday or gotcha day of a visible member."""

    member: HouseholdResponse
    occasion: Literal["birthday", "gotcha_day"]
    in_days: int
