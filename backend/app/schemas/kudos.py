"""
@file kudos.py
@brief Pydantic schemas for the kudos (shoutout) feature.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class KudosCreate(BaseModel):
    """@brief Request body for creating a kudos."""

    recipient_id: uuid.UUID
    message: str | None = Field(default=None, max_length=2000)
    subgroup_id: uuid.UUID | None = None


class KudosRecipient(BaseModel):
    """@brief Minimal recipient profile embedded in a kudos."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    display_name: str
    avatar_url: str | None = None


class KudosResponse(BaseModel):
    """@brief A kudos with recipient data."""

    id: uuid.UUID
    recipient_id: uuid.UUID
    message: str | None
    author_id: uuid.UUID
    subgroup_id: uuid.UUID | None = None
    created_at: datetime
    recipient: KudosRecipient | None = None


class KudosList(BaseModel):
    """@brief Paginated kudos list."""

    kudos: list[KudosResponse]
    pagination: dict[str, str | bool | None]
