"""@file Built-in `gentle_nudge` notification type.

@brief Payload schema and registration for `gentle_nudge`.
"""

from app.services.notifications.registry import (
    NotificationPayload,
    NotificationType,
    register,
)


class GentleNudgePayload(NotificationPayload):
    """@brief Payload for gentle_nudge notifications."""


GENTLE_NUDGE_TYPE = NotificationType(
    key="gentle_nudge",
    category="social",
    payload_schema=GentleNudgePayload,
    default_channels={"inapp": True, "email": False, "push": False, "toast": False},
    group_window_seconds=None,
    toast_on_arrival=False,
    label_i18n="notif.gentle_nudge.label",
    icon="bell",
)
register(GENTLE_NUDGE_TYPE)
