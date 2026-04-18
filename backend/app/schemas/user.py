"""
@file user.py
@brief Pydantic schemas for user profile request/response payloads.

Provides public and private user representations, update payloads,
and paginated list responses.
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl

from app.schemas.auth import SelfHostEmail


class UserResponse(BaseModel):
    """@brief Public user profile visible to other community members."""

    id: UUID
    username: str
    display_name: str
    avatar_url: str | None = None
    bio: str | None = None
    title: str | None = None
    location: str | None = None
    website_url: str | None = None
    role: str
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
    location: str | None = None
    website_url: str | None = None
    birthday: date | None = None
    role: str
    totp_enabled: bool
    storage_used: int
    storage_quota: int
    created_at: datetime
    updated_at: datetime
    last_seen_at: datetime | None = None

    model_config = {"from_attributes": True}


class UserUpdateRequest(BaseModel):
    """@brief Partial update payload for user profile fields."""

    display_name: str | None = Field(None, min_length=1, max_length=100)
    bio: str | None = Field(None, max_length=500)
    title: str | None = Field(None, max_length=50)
    location: str | None = Field(None, max_length=100)
    website_url: HttpUrl | str | None = None
    birthday: date | None = None


class PasswordChangeRequest(BaseModel):
    """@brief Payload for changing the current user's password."""

    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=12)


class EmailChangeRequest(BaseModel):
    """@brief Payload for changing the current user's email."""

    new_email: SelfHostEmail
    password: str = Field(..., min_length=1, description="Current password for verification")
