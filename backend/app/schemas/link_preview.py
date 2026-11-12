"""
@file link_preview.py
@brief Pydantic schemas for the link preview endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class LinkPreviewResponse(BaseModel):
    """
    @brief Public representation of a cached link preview.

    @param cache_ttl_seconds Seconds until the cached entry expires (>= 0).
    """

    id: uuid.UUID
    url: str
    og_title: str
    og_description: str | None = None
    og_image: str | None = None
    og_site_name: str | None = None
    provider_type: str | None = None
    provider_id: str | None = None
    created_at: datetime
    cache_ttl_seconds: int


class ScrapeRequest(BaseModel):
    """@brief Body for POST /link-previews/scrape."""

    url: str = Field(min_length=8, max_length=2048, pattern=r"^https?://")


class ScrapeResponse(BaseModel):
    """@brief Acknowledgement that a scrape task was enqueued."""

    status: str
