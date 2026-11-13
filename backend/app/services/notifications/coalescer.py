"""
@file coalescer.py
@brief Group-key composition for windowed notification coalescing.
"""

from __future__ import annotations

from typing import Any

from app.services.notifications.registry import NotificationType


def compose_group_key(type_: NotificationType, payload: dict[str, Any]) -> str | None:
    """
    @brief Compose the coalescing key for a notification.

    @param type_ Registered notification type.
    @param payload Validated payload dict.
    @return "<type.key>:<target_id>" when the type has a window and the
        payload has a target_id, else None.
    """
    target_id = payload.get("target_id")
    if not type_.group_window_seconds or not target_id:
        return None
    return f"{type_.key}:{target_id}"
