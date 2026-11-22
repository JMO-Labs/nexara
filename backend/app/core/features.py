"""
@file features.py
@brief Per-community feature flags stored in ``communities.features`` (JSONB).
       Unset keys fall back to ``FEATURE_DEFAULTS``.
"""

from __future__ import annotations

from app.core.exceptions import AppError
from app.models.community import Community

FEATURE_DEFAULTS: dict[str, bool] = {
    "recap": True,
    "on_this_day": True,
    "daily_question": True,
    "time_capsules": True,
    "event_albums": True,
    "recipes": True,
    "memorials": True,
    "expenses": True,
    "rides": True,
    "chores": True,
    "relations": True,
    "family_tree": True,
    "reconnect_nudges": True,
    "safe_arrival": True,
    "voice_stories": True,
    "simple_mode": True,
    "newsletter": True,
    "reply_by_email": False,
}
"""@brief Every flag key with its default (all on except ``reply_by_email``)."""


def is_enabled(community: Community, key: str) -> bool:
    """
    @param community The community row.
    @param key Feature key from ``FEATURE_DEFAULTS``.
    @return Whether the feature is on for this community.
    @throws KeyError on an unknown key.
    """
    default = FEATURE_DEFAULTS[key]
    return bool((community.features or {}).get(key, default))


def require_feature(community: Community, key: str) -> None:
    """
    @brief Guard for service entry points.
    @throws AppError FEATURE_DISABLED (404) when the feature is off.
    """
    if not is_enabled(community, key):
        raise AppError(code="FEATURE_DISABLED", message="Feature is disabled", status_code=404)
