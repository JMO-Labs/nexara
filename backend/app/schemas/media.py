"""
@file media.py
@brief Pydantic schemas for media upload, metadata, and responses.

Used by the media API endpoints and service layer for validation
and serialization of media records.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

MediaStatus = Literal["processing", "ready", "error"]
"""@brief Allowed media processing status values."""


class MediaResponse(BaseModel):
    """
    @brief Public media metadata returned by GET /api/v1/media/{id}.

    Includes storage keys for serving original and thumbnail files.
    """

    id: UUID
    filename: str
    content_type: str
    storage_key: str
    thumbnail_key: str | None = None
    size_bytes: int
    width: int | None = None
    height: int | None = None
    alt_text: str | None = None
    status: MediaStatus
    created_at: datetime

    model_config = {"from_attributes": True}
