"""
@file presence.py
@brief Schemas for POST /api/v1/presence.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class PresenceRequest(BaseModel):
    """@brief User ids whose presence the viewer wants (1..200)."""

    user_ids: list[UUID] = Field(min_length=1, max_length=200)


class PresenceResponse(BaseModel):
    """@brief Online ids and last-seen times, privacy flags already applied."""

    online: list[UUID]
    last_seen: dict[UUID, datetime | None]
