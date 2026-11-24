"""
@file user.py
@brief Pydantic schemas for user profile request/response payloads.

Provides public and private user representations, update payloads,
and paginated list responses.
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID
from zoneinfo import available_timezones

from pydantic import BaseModel, Field, HttpUrl, field_validator

from app.schemas.auth import SelfHostEmail
from app.schemas.profile import plausible_birthday


class UserResponse(BaseModel):
    """@brief Public user profile visible to other community members."""

    id: UUID
    username: str
    display_name: str
    avatar_url: str | None = None
    bio: str | None = None
    title: str | None = None
    pronouns: str | None = None
    location: str | None = None
    website_url: str | None = None
    role: str
    is_bot: bool = False
    created_at: datetime
    last_seen_at: datetime | None = None

    model_config = {"from_attributes": True}


class UserDetailResponse(BaseModel):
    """
    @brief Detailed user profile returned to the authenticated user themselves.

    Includes private fields like email, 2FA status, and storage usage.
    """

    id: UUID
    username: str
    display_name: str
    email: str
    email_verified: bool
    avatar_url: str | None = None
    bio: str | None = None
    title: str | None = None
    pronouns: str | None = None
    location: str | None = None
    website_url: str | None = None
    birthday: date | None = None
    timezone: str | None = None
    banner_media_id: UUID | None = None
    phone: str | None = None
    contact_email: str | None = None
    address: str | None = None
    links: list[dict[str, str]] = []
    emergency_contact: dict[str, str] | None = None
    skills: list[str] = []
    availability: str | None = None
    dietary: str | None = None
    role: str
    is_bot: bool = False
    totp_enabled: bool
    storage_used: int
    storage_quota: int
    created_at: datetime
    updated_at: datetime
    last_seen_at: datetime | None = None
    tour_completed_at: datetime | None = None
    age_group: str | None = None  # effective (read-only); set by /users/me
    # admin | birthday | approval_pending | unknown (read-only); set by /users/me
    age_group_source: str | None = None

    model_config = {"from_attributes": True}


class UserUpdateRequest(BaseModel):
    """@brief Partial update payload for user profile fields."""

    display_name: str | None = Field(None, min_length=1, max_length=100)
    bio: str | None = Field(None, max_length=500)
    title: str | None = Field(None, max_length=50)
    pronouns: str | None = Field(None, max_length=50, description="User pronouns")
    location: str | None = Field(None, max_length=100)
    website_url: HttpUrl | None = None
    birthday: date | None = None
    timezone: str | None = Field(None, max_length=64, description="IANA timezone")

    @field_validator("birthday")
    @classmethod
    def _birthday(cls, v: date | None) -> date | None:
        """@brief 1900 or later, not in the future."""
        return plausible_birthday(v)

    @field_validator("timezone")
    @classmethod
    def _tz(cls, v: str | None) -> str | None:
        """@brief Must be a known IANA zone."""
        if v is not None and v not in available_timezones():
            raise ValueError("Unknown timezone")
        return v


class PasswordChangeRequest(BaseModel):
    """@brief Payload for changing the current user's password."""

    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=12)


class EmailChangeRequest(BaseModel):
    """@brief Payload for changing the current user's email."""

    new_email: SelfHostEmail
    password: str = Field(..., min_length=1, description="Current password for verification")
