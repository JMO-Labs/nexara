"""@file Effective per-channel notification preference resolution.

@brief Merges a type's default channels with user overrides.
"""

from typing import Any

from app.services.notifications.registry import Channel, NotificationType

_CHANNELS: tuple[Channel, ...] = ("inapp", "email", "push", "toast")


def effective_channels(
    type: NotificationType,  # noqa: A002
    user_prefs: dict[str, Any],
) -> dict[Channel, bool]:
    """@brief Compute per-channel on/off map: defaults + user overrides.

    @param type Registered notification type.
    @param user_prefs Per-type user overrides keyed by type key.
    @return Map with inapp, email, push, toast always present; overrides
        apply only to channels in ``type.user_configurable``.
    """
    out: dict[Channel, bool] = dict(type.default_channels)
    for ch in _CHANNELS:
        if ch not in out:
            out[ch] = False
    overrides = user_prefs.get(type.key) or {}
    for ch, value in overrides.items():
        if ch in type.user_configurable:
            out[ch] = bool(value)
    return out
