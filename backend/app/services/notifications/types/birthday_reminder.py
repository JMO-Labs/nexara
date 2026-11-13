"""@file Built-in `birthday_reminder` notification type.

@brief Payload schema and registration for `birthday_reminder`.
"""

from app.services.notifications.registry import (
    NotificationPayload,
    NotificationType,
    register,
)


class BirthdayReminderPayload(NotificationPayload):
    """@brief Payload for birthday_reminder notifications."""

    user_id: str | None = None


BIRTHDAY_TYPE = NotificationType(
    key="birthday_reminder",
    category="social",
    payload_schema=BirthdayReminderPayload,
    default_channels={"inapp": True, "email": False, "push": False, "toast": False},
    group_window_seconds=None,
    toast_on_arrival=False,
    label_i18n="notif.birthday_reminder.label",
    icon="cake",
)
register(BIRTHDAY_TYPE)
