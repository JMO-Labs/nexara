"""
@file profile.py
@brief Profile field schemas: link/emergency-contact shapes, the update
       payload (PUT /settings/profile) and the viewer-filtered profile.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

Level = Literal["private", "groups", "community"]

_URL = r"^https?://\S+$"


class LinkItem(BaseModel):
    """@brief A profile link; socials get a brand glyph from the URL host."""

    label: str = Field(default="", max_length=40)
    url: str = Field(..., max_length=300, pattern=_URL)


class EmergencyContact(BaseModel):
    """@brief Who to call in an emergency."""

    name: str = Field(..., min_length=1, max_length=100)
    phone: str = Field(..., min_length=3, max_length=40)
    relation: str = Field(default="", max_length=40)


class ProfileUpdate(BaseModel):
    """
    @brief Partial profile update. Omitted fields are untouched; null or ""
           clears an optional field. ``field_visibility`` merges per field.
    """

    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    bio: str | None = Field(default=None, max_length=500)
    title: str | None = Field(default=None, max_length=50)
    pronouns: str | None = Field(default=None, max_length=50)
    location: str | None = Field(default=None, max_length=100)
    website_url: str | None = Field(default=None, max_length=300, pattern=r"^(https?://\S+)?$")
    birthday: date | None = None
    banner_media_id: UUID | None = None
    avatar_media_id: UUID | None = None  # uploaded photo; null removes it
    phone: str | None = Field(default=None, max_length=40)
    contact_email: EmailStr | Literal[""] | None = None
    address: str | None = Field(default=None, max_length=300)
    links: list[LinkItem] | None = Field(default=None, max_length=12)
    emergency_contact: EmergencyContact | None = None
    skills: list[str] | None = Field(default=None, max_length=20)
    availability: str | None = Field(default=None, max_length=200)
    dietary: str | None = Field(default=None, max_length=300)
    field_visibility: dict[str, Level] | None = None
    # Opt in to showing your Gravatar (sends a hash of your email to gravatar.com).
    use_gravatar: bool | None = None
    # Private email used only for the Gravatar hash ("" clears it).
    gravatar_email: EmailStr | Literal[""] | None = Field(default=None, max_length=254)

    @field_validator("skills")
    @classmethod
    def _skills(cls, v: list[str] | None) -> list[str] | None:
        """@brief Trim, drop blanks/dupes, cap each at 40 chars."""
        if v is None:
            return v
        out: list[str] = []
        for s in v:
            s = s.strip()[:40]
            if s and s.lower() not in {o.lower() for o in out}:
                out.append(s)
        return out


class ProfileResponse(BaseModel):
    """@brief A member profile with fields the viewer may not see set to null."""

    id: UUID
    username: str
    display_name: str
    avatar_url: str | None = None
    role: str
    created_at: datetime
    last_seen_at: datetime | None = None
    banner_media_id: UUID | None = None
    memorialized_at: datetime | None = None
    passed_on: date | None = None
    bio: str | None = None
    title: str | None = None
    pronouns: str | None = None
    location: str | None = None
    website_url: str | None = None
    birthday: str | None = None
    phone: str | None = None
    contact_email: str | None = None
    address: str | None = None
    links: list[LinkItem] = Field(default_factory=list)
    emergency_contact: EmergencyContact | None = None
    skills: list[str] = Field(default_factory=list)
    availability: str | None = None
    dietary: str | None = None
    # Only on your own profile: the resolved level of every field.
    field_visibility: dict[str, Level] | None = None


class UserSummaryResponse(BaseModel):
    """@brief Name and avatar only (pickers, blocked list)."""

    id: UUID
    username: str
    display_name: str
    avatar_url: str | None = None

    model_config = {"from_attributes": True}
