"""@file Built-in `kudos_received` notification type.

@brief Payload schema and registration for `kudos_received`.
"""

from app.services.notifications.registry import (
    NotificationPayload,
    NotificationType,
    register,
)


class KudosReceivedPayload(NotificationPayload):
    """@brief Payload for kudos_received notifications."""


KUDOS_TYPE = NotificationType(
    key="kudos_received",
    category="social",
    payload_schema=KudosReceivedPayload,
    default_channels={"inapp": True, "email": False, "push": False, "toast": True},
    group_window_seconds=None,
    toast_on_arrival=True,
    label_i18n="notif.kudos_received.label",
    icon="heart",
)
register(KUDOS_TYPE)
