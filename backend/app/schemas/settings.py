"""
@file settings.py
@brief Pydantic schemas for user settings endpoints.

Phase 1 exposes notification preferences (per-type x per-channel toggles)
and basic profile settings. Privacy and appearance settings ship in Phase 2.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class WidgetInstanceSchema(BaseModel):
    """@brief Typed schema for a single persisted widget instance.

    Layout coordinates are react-grid-layout-compatible: x, y, w, h on a
    12-column grid. `collapsed` is independent of the grid coordinates.
    """

    id: str = Field(..., max_length=64)
    def_id: str = Field(..., max_length=64, alias="defId")
    x: int = Field(..., ge=0, le=12)
    y: int = Field(..., ge=0)
    w: int = Field(..., ge=1, le=12)
    h: int = Field(..., ge=1)
    collapsed: bool
    props: dict[str, Any] | None = None

    model_config = {"populate_by_name": True, "extra": "ignore"}


class HomeLayoutSchema(BaseModel):
    """@brief Typed schema for the persisted home page widget layout."""

    widgets: list[WidgetInstanceSchema] = Field(..., max_length=64)


class NotificationPreferences(BaseModel):
    """
    @brief Per-type notification channel toggles.

    Phase 1 types: mention, comment, reaction, new_post, system, invite_accepted.
    Each type has inapp and email booleans (push deferred to Phase 2).
    """

    notif_mention_inapp: bool | None = None
    notif_mention_email: bool | None = None
    notif_comment_inapp: bool | None = None
    notif_comment_email: bool | None = None
    notif_reaction_inapp: bool | None = None
    notif_reaction_email: bool | None = None
    notif_new_post_inapp: bool | None = None
    notif_new_post_email: bool | None = None
    notif_system_inapp: bool | None = None
    notif_system_email: bool | None = None
    notif_invite_accepted_inapp: bool | None = None
    notif_invite_accepted_email: bool | None = None
    mute_all_email: bool | None = None


class UserSettingsResponse(BaseModel):
    """@brief Full user settings response."""

    notif_mention_inapp: bool
    notif_mention_email: bool
    notif_comment_inapp: bool
    notif_comment_email: bool
    notif_reaction_inapp: bool
    notif_reaction_email: bool
    notif_new_post_inapp: bool
    notif_new_post_email: bool
    notif_system_inapp: bool
    notif_system_email: bool
    notif_invite_accepted_inapp: bool
    notif_invite_accepted_email: bool
    mute_all_email: bool
    theme: str
    locale: str
    home_layout: HomeLayoutSchema | None = None

    model_config = {"from_attributes": True}


class UserSettingsUpdate(BaseModel):
    """@brief Partial update payload for user settings."""

    theme: str | None = Field(default=None, pattern=r"^(system|light|dark)$")
    locale: str | None = Field(default=None, max_length=10)
    home_layout: HomeLayoutSchema | None = None


class ProfileUpdate(BaseModel):
    """@brief Payload for updating user profile fields."""

    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    bio: str | None = Field(default=None, max_length=500)
    location: str | None = Field(default=None, max_length=100)
    website_url: str | None = Field(default=None, max_length=300)
    title: str | None = Field(default=None, max_length=50)
