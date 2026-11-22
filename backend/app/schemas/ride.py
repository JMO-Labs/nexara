"""
@file ride.py
@brief Pydantic schemas for event rides.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class RideCreate(BaseModel):
    """@brief Body for offering or requesting a ride (``seats`` = offered or needed)."""

    seats: int = Field(ge=1, le=8)
    origin: str = Field(default="", max_length=120)
    depart_at: datetime | None = None
    note: str = Field(default="", max_length=200)

    @field_validator("depart_at")
    @classmethod
    def _utc(cls, v: datetime | None) -> datetime | None:
        """@brief Naive input is taken as UTC; stored as UTC."""
        if v is None:
            return None
        return v.replace(tzinfo=UTC) if v.tzinfo is None else v.astimezone(UTC)


class RideAnswer(BaseModel):
    """@brief Body for answering a request with one of the driver's offers."""

    offer_id: uuid.UUID


class RidePassengerOut(BaseModel):
    """@brief A passenger visible to the viewer."""

    user_id: uuid.UUID
    display_name: str


class RideOut(BaseModel):
    """@brief One offer or request with passengers and seats left."""

    id: uuid.UUID
    event_id: uuid.UUID
    kind: Literal["offer", "request"]
    user_id: uuid.UUID
    driver_name: str
    seats: int
    seats_left: int
    origin: str
    depart_at: datetime | None
    note: str
    passengers: list[RidePassengerOut]
    joined: bool
    created_at: datetime
