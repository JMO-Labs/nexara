"""
@file media.py
@brief Pydantic schemas for media upload, metadata, and responses.

Used by the media API endpoints and service layer for validation
and serialization of media records.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, field_validator

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
    duration_secs: float | None = None
    alt_text: str | None = None
    status: MediaStatus
    created_at: datetime

    @field_validator("duration_secs", mode="before")
    @classmethod
    def _coerce_duration(cls, v: object) -> float | None:
        if v is None:
            return None
        if isinstance(v, Decimal):
            return float(v)
        return v  # type: ignore[return-value] # validator returns narrowed runtime type

    model_config = {"from_attributes": True}


class MultipartInitRequest(BaseModel):
    """@brief Request body for initiating a multipart upload."""

    filename: str
    content_type: str
    total_size: int


class MultipartInitResponse(BaseModel):
    """@brief Response with upload ID and part size for multipart upload."""

    upload_id: str
    part_size: int


class MultipartPartResponse(BaseModel):
    """@brief Response for each uploaded part."""

    part_number: int
    etag: str


class MultipartCompleteResponse(BaseModel):
    """@brief Response after completing multipart upload."""

    media_id: UUID


class StorageByType(BaseModel):
    """@brief Per-category storage usage in bytes."""

    photos: int = 0
    videos: int = 0
    documents: int = 0
    other: int = 0


class StorageUsageResponse(BaseModel):
    """@brief Response for GET /api/v1/users/{user_id}/storage."""

    used_bytes: int
    quota_bytes: int
    by_type: StorageByType
