"""@file Registry-backed helpers for the notification API.

@brief Type/category filter resolution, category grouping and preference
patch validation. Errors use the standard envelope codes
``NOTIF_TYPE_UNKNOWN`` and ``NOTIF_PREF_INVALID`` (400).
"""

from __future__ import annotations

from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.exceptions import AppError
from app.schemas.notification import DIGEST_CADENCES, NotificationPreferencesUpdate
from app.services.notifications import registry
from app.services.notifications.registry import NotificationType

FALLBACK_CATEGORY = "system"
"""@brief Category used for rows whose type is no longer registered."""


def unknown_type(key: str) -> AppError:
    """@brief Build the NOTIF_TYPE_UNKNOWN (400) error.

    @param key The offending type key.
    """
    return AppError(
        code="NOTIF_TYPE_UNKNOWN",
        message=f"Unknown notification type: {key}",
        status_code=400,
        details={"type": key},
    )


def pref_invalid(message: str, field: str) -> AppError:
    """@brief Build the NOTIF_PREF_INVALID (400) error.

    @param message Human-readable reason.
    @param field Offending field path.
    """
    return AppError(
        code="NOTIF_PREF_INVALID",
        message=message,
        status_code=400,
        details={"field": field},
    )


def get_type(key: str) -> NotificationType:
    """@brief Registry lookup raising NOTIF_TYPE_UNKNOWN.

    @param key Type key.
    @return The registered type.
    """
    try:
        return registry.get(key)
    except KeyError:
        raise unknown_type(key) from None


def resolve_types(type_key: str | None, category: str | None) -> list[str] | None:
    """@brief Turn optional type/category filters into a type-key list.

    @param type_key Single type filter.
    @param category Category filter (expanded to its registered type keys).
    @return Key list to filter on, or None for no filter.
    """
    keys: list[str] | None = None
    if category is not None:
        keys = [t.key for t in registry.iter_types() if t.category == category]
    if type_key is not None:
        get_type(type_key)
        keys = [type_key] if keys is None or type_key in keys else []
    return keys


def group_by_category(counts: dict[str, int]) -> dict[str, int]:
    """@brief Fold per-type counts into per-category counts.

    @param counts {type_key: count}.
    @return {category: count}; unregistered types count as ``system``.
    """
    out: dict[str, int] = {}
    for key, n in counts.items():
        try:
            cat: str = registry.get(key).category
        except KeyError:
            cat = FALLBACK_CATEGORY
        out[cat] = out.get(cat, 0) + n
    return out


def build_prefs_update(
    patch: NotificationPreferencesUpdate, current_prefs: dict[str, Any]
) -> dict[str, Any]:
    """@brief Validate a preferences patch and build the column update dict.

    ``notification_prefs`` is merged per type/channel into ``current_prefs``;
    other fields replace the stored value. Only fields set in the body apply.

    @param patch Parsed PATCH body.
    @param current_prefs Stored ``notification_prefs``.
    @return Column -> new value.
    @throws AppError NOTIF_TYPE_UNKNOWN / NOTIF_PREF_INVALID.
    """
    data: dict[str, Any] = {}
    fields = patch.model_fields_set
    if "notification_prefs" in fields:
        merged = {k: dict(v) for k, v in current_prefs.items()}
        for key, channels in (patch.notification_prefs or {}).items():
            type_ = get_type(key)
            for ch in channels:
                if ch not in type_.user_configurable:
                    raise pref_invalid(
                        f"Channel '{ch}' is not configurable for {key}",
                        f"notification_prefs.{key}.{ch}",
                    )
            for ch, value in channels.items():
                if not isinstance(value, bool):
                    raise pref_invalid(
                        f"Value for '{ch}' must be a boolean",
                        f"notification_prefs.{key}.{ch}",
                    )
            merged[key] = {**merged.get(key, {}), **channels}
        data["notification_prefs"] = merged
    if "dnd_schedule" in fields:
        data["dnd_schedule"] = patch.dnd_schedule
    if "dnd_timezone" in fields:
        tz = patch.dnd_timezone
        try:
            ZoneInfo(tz or "")
        except (ZoneInfoNotFoundError, ValueError, OSError):
            raise pref_invalid(f"Unknown timezone: {tz}", "dnd_timezone") from None
        data["dnd_timezone"] = tz
    if "digest_cadence" in fields:
        cadence = patch.digest_cadence or {}
        for key, value in cadence.items():
            get_type(key)
            if value not in DIGEST_CADENCES:
                raise pref_invalid(
                    f"Invalid digest cadence '{value}' for {key}", f"digest_cadence.{key}"
                )
        data["digest_cadence"] = cadence
    return data
