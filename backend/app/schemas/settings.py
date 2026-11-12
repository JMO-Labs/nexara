"""
@file settings.py
@brief Pydantic schemas for user settings endpoints.

Phase 1 exposes notification preferences (per-type x per-channel toggles)
and basic profile settings. Privacy and appearance settings ship in Phase 2.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, create_model, field_validator

DEFAULT_WIDGET_ORDER: list[str] = ["upcoming-events", "my-groups", "media", "quick-actions"]


class HomeLayoutSchema(BaseModel):
    """@brief Persisted home widget column: display order plus hidden widget ids."""

    order: list[str] = Field(default_factory=lambda: list(DEFAULT_WIDGET_ORDER), max_length=16)
    hidden: list[str] = Field(default_factory=list, max_length=16)

    model_config = {"extra": "forbid"}


def _tolerant_layout(value: Any) -> Any:
    """@brief Map any stored shape other than the list layout to the default layout."""
    if value is None or isinstance(value, HomeLayoutSchema):
        return value
    try:
        return HomeLayoutSchema.model_validate(value)
    except ValueError:
        return HomeLayoutSchema()


NOTIF_TYPES: tuple[str, ...] = (
    "mention",
    "comment",
    "reaction",
    "new_post",
    "system",
    "invite_accepted",
    "event_reminder",
    "event_rsvp",
    "gallery_activity",
    "prompt",
    "prompt_summary",
    "poll",
    "dm",
    "birthday",
)
NOTIF_CHANNELS: tuple[str, ...] = ("inapp", "email", "push")

# Declared once and expanded into 14 types x 3 channels optional bool fields.
_TOGGLE_FIELDS: dict[str, Any] = {
    f"notif_{t}_{c}": (bool | None, None) for t in NOTIF_TYPES for c in NOTIF_CHANNELS
}

_NotificationToggles = create_model("_NotificationToggles", **_TOGGLE_FIELDS)


class NotificationPreferences(_NotificationToggles):  # type: ignore[valid-type,misc]
    """
    @brief Notification preferences: per-type x per-channel toggles plus globals.

    Toggle fields are named ``notif_<type>_<channel>`` (see NOTIF_TYPES and
    NOTIF_CHANNELS). Also carries global mutes and email digest settings.
    """

    mute_all_email: bool | None = None
    mute_all_push: bool | None = None
    email_digest_enabled: bool | None = None
    email_digest_hour: int | None = Field(default=None, ge=0, le=23)


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
    profile_visible_to: str = "community"
    show_online_status: bool = True
    show_last_seen: bool = True
    show_birthday_to: str = "community"
    show_birthday_year: bool = False
    allow_sassybot: bool = True
    font_size: str = "medium"
    compact_feed: bool = False
    home_layout: HomeLayoutSchema | None = None

    model_config = {"from_attributes": True}

    _legacy_layout = field_validator("home_layout", mode="before")(_tolerant_layout)


class UserSettingsUpdate(BaseModel):
    """@brief Partial update payload for user settings."""

    theme: str | None = Field(default=None, pattern=r"^(system|light|dark)$")
    locale: str | None = Field(default=None, max_length=10)
    profile_visible_to: str | None = Field(default=None, pattern=r"^(community|admin_only)$")
    show_online_status: bool | None = None
    show_last_seen: bool | None = None
    show_birthday_to: str | None = Field(default=None, pattern=r"^(nobody|community|admin_only)$")
    show_birthday_year: bool | None = None
    allow_sassybot: bool | None = None
    font_size: str | None = Field(default=None, pattern=r"^(small|medium|large)$")
    compact_feed: bool | None = None
    home_layout: HomeLayoutSchema | None = None


class ProfileUpdate(BaseModel):
    """@brief Payload for updating user profile fields."""

    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    bio: str | None = Field(default=None, max_length=500)
    location: str | None = Field(default=None, max_length=100)
    website_url: str | None = Field(default=None, max_length=300)
    title: str | None = Field(default=None, max_length=50)
