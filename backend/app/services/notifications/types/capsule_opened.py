"""@file Built-in `capsule_opened` notification type.

@brief Payload schema and registration for `capsule_opened`.
"""

from app.services.notifications.registry import (
    NotificationPayload,
    NotificationType,
    register,
)


class CapsuleOpenedPayload(NotificationPayload):
    """@brief Payload for capsule_opened notifications."""

    capsule_id: str
    title: str
    author_name: str


CAPSULE_OPENED_TYPE = NotificationType(
    key="capsule_opened",
    category="social",
    payload_schema=CapsuleOpenedPayload,
    default_channels={"inapp": True, "email": False, "push": True, "toast": True},
    group_window_seconds=None,
    toast_on_arrival=True,
    label_i18n="notif.capsule_opened.label",
    icon="hourglass",
)
register(CAPSULE_OPENED_TYPE)
