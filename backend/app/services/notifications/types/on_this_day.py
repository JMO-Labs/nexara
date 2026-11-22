"""@file Built-in `on_this_day` notification type.

@brief Payload schema and registration for `on_this_day` (daily memories nudge).
"""

from app.services.notifications.registry import (
    NotificationPayload,
    NotificationType,
    register,
)


class OnThisDayPayload(NotificationPayload):
    """@brief Payload for on_this_day notifications."""

    count: int = 0


ON_THIS_DAY_TYPE = NotificationType(
    key="on_this_day",
    category="social",
    payload_schema=OnThisDayPayload,
    default_channels={"inapp": True, "email": False, "push": False, "toast": False},
    group_window_seconds=None,
    toast_on_arrival=False,
    label_i18n="notif.on_this_day.label",
    icon="history",
)
register(ON_THIS_DAY_TYPE)
