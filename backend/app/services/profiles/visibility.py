"""
@file visibility.py
@brief Per-field profile privacy. Each optional field has a level:
       private (owner only), groups (people sharing a group) or community.
       Fields predating per-field privacy default to the legacy
       profile_visible_to; fields added with it default to private.
"""

from __future__ import annotations

from typing import Any, Literal

Level = Literal["private", "groups", "community"]
LEVELS: tuple[Level, ...] = ("private", "groups", "community")

LEGACY_FIELDS = ("bio", "title", "pronouns", "location", "website_url")
NEW_FIELDS = (
    "phone",
    "contact_email",
    "address",
    "links",
    "emergency_contact",
    "skills",
    "availability",
    "dietary",
)
FIELDS = LEGACY_FIELDS + NEW_FIELDS


def effective_levels(stored: dict[str, str] | None, profile_visible_to: str) -> dict[str, Level]:
    """
    @brief Resolve each field's level from stored choices plus defaults.
    @param stored user_settings.field_visibility (may be partial or stale)
    @param profile_visible_to legacy whole-profile setting
    """
    legacy: Level = "community" if profile_visible_to == "community" else "private"
    out: dict[str, Level] = {}
    for f in FIELDS:
        v = (stored or {}).get(f)
        out[f] = v if v in LEVELS else (legacy if f in LEGACY_FIELDS else "private")  # type: ignore[assignment]
    return out


def allowed(level: Level, *, is_self: bool, shares_group: bool) -> bool:
    """@brief Can this viewer see a field at ``level``?"""
    if is_self or level == "community":
        return True
    return level == "groups" and shares_group


def birthday_view(
    birthday: Any, *, is_self: bool, show_to: str, show_year: bool, viewer_is_admin: bool
) -> str | None:
    """
    @brief ISO ``YYYY-MM-DD``, ``--MM-DD`` when the year is hidden, or None.
    """
    if birthday is None:
        return None
    if not is_self and not (
        show_to == "community" or (show_to == "admin_only" and viewer_is_admin)
    ):
        return None
    if is_self or show_year:
        return str(birthday.isoformat())
    return f"--{birthday.month:02d}-{birthday.day:02d}"
