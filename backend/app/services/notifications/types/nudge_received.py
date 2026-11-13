"""@file Built-in `nudge_received` notification type.

@brief Payload schema and registration for `nudge_received`.
"""

from app.services.notifications.registry import (
    NotificationPayload,
    NotificationType,
    register,
)


class NudgeReceivedPayload(NotificationPayload):
    """@brief Payload for nudge_received notifications."""


NUDGE_TYPE = NotificationType(
    key="nudge_received",
    category="social",
    payload_schema=NudgeReceivedPayload,
    default_channels={"inapp": True, "email": False, "push": False, "toast": True},
    group_window_seconds=None,
    toast_on_arrival=True,
    label_i18n="notif.nudge_received.label",
    icon="hand",
)
register(NUDGE_TYPE)
