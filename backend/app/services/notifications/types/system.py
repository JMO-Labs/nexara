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
    default_channels={"inapp": True, "email": True, "push": False},
    group_window_seconds=None,
    toast_on_arrival=True,
    label_i18n="notifications.types.system",
    icon="info",
)
register(SYSTEM_TYPE)
