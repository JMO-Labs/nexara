"""@file Built-in `system` notification type.

@brief Payload schema and registration for `system`.
"""

from app.services.notifications.registry import (
    NotificationPayload,
    NotificationType,
    register,
)


class SystemPayload(NotificationPayload):
    """@brief Payload for system notifications."""


SYSTEM_TYPE = NotificationType(
    key="system",
    category="system",
    payload_schema=SystemPayload,
    default_channels={"inapp": True, "email": True, "push": True, "toast": True},
    group_window_seconds=None,
    bypass_dnd=True,
    toast_on_arrival=True,
    label_i18n="notif.system.label",
    icon="info",
)
register(SYSTEM_TYPE)
