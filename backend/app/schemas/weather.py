"""
@file weather.py
@brief Weather API schemas (temperatures in Celsius; clients convert).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PlaceCreate(BaseModel):
    """@brief Save a weather place."""

    name: str = Field(..., min_length=1, max_length=80)
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)


class PlaceResponse(BaseModel):
    """@brief A saved place."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    lat: float
    lon: float
    created_at: datetime


class Current(BaseModel):
    """@brief Conditions now."""

    temp_c: float | None = None
    code: int | None = None
    is_day: bool = True


class Day(BaseModel):
    """@brief One forecast day."""

    date: date
    code: int | None = None
    max_c: float | None = None
    min_c: float | None = None
    precip: int | None = None


class Forecast(BaseModel):
    """@brief Current + daily forecast."""

    current: Current
    daily: list[Day]


class BoardItem(BaseModel):
    """@brief One location on the weather board."""

    id: str
    kind: Literal["self", "place", "person"]
    label: str
    place: str | None = None
    lat: float
    lon: float
    user_id: UUID | None = None
    avatar_url: str | None = None
    forecast: Forecast | None = None
