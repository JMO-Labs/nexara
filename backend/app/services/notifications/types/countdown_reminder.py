"""@file Built-in `countdown_reminder` notification type.

@brief Reminder (7 days, 1 day, day-of) for a followed countdown.
"""

from app.services.notifications.registry import (
    NotificationPayload,
    NotificationType,
    register,
)


class CountdownReminderPayload(NotificationPayload):
    """@brief Payload for countdown_reminder notifications."""


COUNTDOWN_REMINDER_TYPE = NotificationType(
    key="countdown_reminder",
    category="social",
    payload_schema=CountdownReminderPayload,
    default_channels={"inapp": True, "email": False, "push": True, "toast": False},
    label_i18n="notif.countdown_reminder.label",
    icon="hourglass",
)
register(COUNTDOWN_REMINDER_TYPE)
