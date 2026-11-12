"""
@file branding.py
@brief Pydantic schemas for community branding endpoints.

Phase 1 exposes community_name, tagline, color_primary, and color_primary_dark.
Full palette customization ships in Phase 2.
"""

from __future__ import annotations

import re
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.services.branding.contrast import contrast_ratio

_ACCENT_TEXT = "#14301E"
"""@brief Forest text colour that sits on the accent colour (light palette)."""

_HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
"""@brief Regex for validating 6-digit hex color strings."""

_COLOR_FIELDS = (
    "color_primary",
    "color_primary_dark",
    "color_accent",
    "color_surface_light",
    "color_surface_dark",
    "color_text_light",
    "color_text_dark",
)


def _validate_hex(v: str | None) -> str | None:
    """@brief Ensure color values are valid 6-digit hex strings."""
    if v is not None and not _HEX_COLOR_RE.match(v):
        msg = f"Invalid hex color: {v}. Must be #RRGGBB format."
        raise ValueError(msg)
    return v


class BrandingResponse(BaseModel):
    """@brief Public branding data returned by GET /api/v1/branding/."""

    community_name: str
    tagline: str | None = None
    color_primary: str
    color_primary_dark: str
    logo_light_url: str | None = None
    logo_dark_url: str | None = None
    # Full palette
    color_accent: str = "#C6B4F5"
    color_surface_light: str = "#ffffff"
    color_surface_dark: str = "#1f2937"
    color_text_light: str = "#111827"
    color_text_dark: str = "#f9fafb"
    font_family: str = "Inter"
    font_family_mono: str = "JetBrains Mono"
    email_logo_media_id: UUID | None = None
    email_footer_text: str | None = None
    email_sender_name: str | None = None
    landing_cta_text: str | None = "Join our community"
    landing_show_feature_list: bool = True
    pwa_icon_192_media_id: UUID | None = None
    pwa_icon_512_media_id: UUID | None = None
    about_short: str | None = None
    custom_css: str | None = None
    custom_css_enabled: bool = False

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
    # Full palette
    color_accent: str | None = None
    color_surface_light: str | None = None
    color_surface_dark: str | None = None
    color_text_light: str | None = None
    color_text_dark: str | None = None
    font_family: str | None = None
    font_family_mono: str | None = None
    email_logo_media_id: UUID | None = None
    email_footer_text: str | None = None
    email_sender_name: str | None = None
    landing_cta_text: str | None = None
    landing_show_feature_list: bool | None = None
    pwa_icon_192_media_id: UUID | None = None
    pwa_icon_512_media_id: UUID | None = None
    about_short: str | None = None
    custom_css: str | None = None
    custom_css_enabled: bool | None = None

    @field_validator(*_COLOR_FIELDS, mode="before")
    @classmethod
    def validate_hex_color(cls, v: str | None) -> str | None:
        """@brief Ensure color values are valid 6-digit hex strings."""
        return _validate_hex(v)

    @field_validator("color_accent", mode="after")
    @classmethod
    def validate_accent_contrast(cls, v: str | None) -> str | None:
        """@brief Reject accents with under 4.5:1 contrast against forest text."""
        if v is not None and contrast_ratio(_ACCENT_TEXT, v) < 4.5:
            msg = "Accent color needs at least 4.5:1 contrast with dark green text."
            raise ValueError(msg)
        return v


class ContrastWarning(BaseModel):
    """@brief WCAG contrast warning for a color pair."""

    color1: str
    color2: str
    ratio: float
    passes_aa: bool
    passes_aaa: bool


class BrandingUpdateResponse(BaseModel):
    """@brief Response for PUT /branding/ with contrast warnings."""

    branding: BrandingResponse
    contrast_warnings: list[ContrastWarning]


class PwaManifest(BaseModel):
    """@brief PWA web app manifest structure."""

    name: str
    short_name: str
    theme_color: str
    background_color: str
    display: str
    start_url: str
    icons: list[dict[str, Any]]


class PresetTheme(BaseModel):
    """@brief A named preset colour theme (all branding colours)."""

    name: str
    description: str
    primary: str
    primary_dark: str
    accent: str
    surface_light: str
    surface_dark: str
    text_light: str
    text_dark: str


class PresetThemeList(BaseModel):
    """@brief Response for GET /branding/presets."""

    themes: list[PresetTheme]
