"""
@file branding.py
@brief Pydantic schemas for community branding endpoints.

Phase 1 exposes community_name, tagline, color_primary, and color_primary_dark.
Full palette customization ships in Phase 2.
"""

from __future__ import annotations

import re
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


_HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
"""@brief Regex for validating 6-digit hex color strings."""


class BrandingResponse(BaseModel):
    """@brief Public branding data returned by GET /api/v1/branding/."""

    community_name: str
    tagline: str | None = None
    color_primary: str
    color_primary_dark: str
    logo_light_url: str | None = None
    logo_dark_url: str | None = None

    model_config = {"from_attributes": True}


class BrandingUpdate(BaseModel):
    """
    @brief Payload for updating community branding (admin only).

    All fields are optional; only provided fields are updated.
    """

    community_name: str | None = Field(default=None, min_length=1, max_length=100)
    tagline: str | None = Field(default=None, max_length=300)
    color_primary: str | None = None
    color_primary_dark: str | None = None
    logo_light_media_id: UUID | None = None
    logo_dark_media_id: UUID | None = None

    @field_validator("color_primary", "color_primary_dark", mode="before")
    @classmethod
    def validate_hex_color(cls, v: str | None) -> str | None:
        """@brief Ensure color values are valid 6-digit hex strings."""
        if v is not None and not _HEX_COLOR_RE.match(v):
            msg = f"Invalid hex color: {v}. Must be #RRGGBB format."
            raise ValueError(msg)
        return v
