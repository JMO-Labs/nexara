"""@file apprise.py
@brief Schemas for the per-user Apprise URL API (the URL is never returned).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AppriseURLCreate(BaseModel):
    """@brief Create payload; ``apprise_url`` is validated by the service."""

    apprise_url: str = Field(min_length=1, max_length=2000)
    label: str | None = Field(default=None, max_length=100)


class AppriseURLUpdate(BaseModel):
    """@brief Partial update."""

    label: str | None = Field(default=None, max_length=100)
    enabled: bool | None = None


class AppriseURLResponse(BaseModel):
    """@brief Public view of a subscription (no URL, encrypted or not)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    label: str | None
    enabled: bool
    failure_count: int
    last_failure_at: datetime | None
    created_at: datetime


class AppriseTestResponse(BaseModel):
    """@brief Result of a test send."""

    status: str
    message: str
