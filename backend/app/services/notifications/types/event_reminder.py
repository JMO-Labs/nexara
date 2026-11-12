"""@file Built-in `event_reminder` notification type.

@brief Payload schema and registration for `event_reminder`.
"""

from datetime import datetime

from app.services.notifications.registry import (
    NotificationPayload,
    NotificationType,
    register,
)


class EventReminderPayload(NotificationPayload):
    """@brief Payload for event_reminder notifications."""

    event_title: str
    starts_at: datetime


EVENTREMINDER_TYPE = NotificationType(
    key="event_reminder",
    category="event",
    payload_schema=EventReminderPayload,
    default_channels={"inapp": True, "email": True, "push": True, "toast": True},
    group_window_seconds=None,
    toast_on_arrival=True,
    label_i18n="notif.event_reminder.label",
    icon="calendar-clock",
)
register(EVENTREMINDER_TYPE)
