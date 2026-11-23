"""
@file trip.py
@brief Pydantic schemas for safe-arrival trips. No location fields exist.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class TripCreate(BaseModel):
    """@brief Request body for starting a trip."""

    label: str = Field(min_length=1, max_length=80)
    expected_at: datetime
    watcher_ids: list[uuid.UUID] = Field(min_length=1, max_length=20)


class TripExtend(BaseModel):
    """@brief Request body for moving the expected arrival time."""

    expected_at: datetime


class TripPerson(BaseModel):
    """@brief Minimal profile of a traveler or watcher."""

    id: uuid.UUID
    display_name: str


class TripOut(BaseModel):
    """@brief A trip as seen by its traveler or a watcher."""

    id: uuid.UUID
    label: str
    expected_at: datetime
    arrived_at: datetime | None = None
    alerted_at: datetime | None = None
    ended_at: datetime | None = None
    traveler: TripPerson
    watchers: list[TripPerson] = Field(default_factory=list)
