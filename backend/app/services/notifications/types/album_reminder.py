"""@file Built-in `album_reminder` notification type.

@brief Payload schema and registration for `album_reminder`.
"""

from app.services.notifications.registry import (
    NotificationPayload,
    NotificationType,
    register,
)


class AlbumReminderPayload(NotificationPayload):
    """@brief Payload for album_reminder notifications."""

    event_id: str
    gallery_id: str
    title: str


ALBUM_REMINDER_TYPE = NotificationType(
    key="album_reminder",
    category="gallery",
    payload_schema=AlbumReminderPayload,
    default_channels={"inapp": True, "email": False, "push": False, "toast": False},
    group_window_seconds=None,
    toast_on_arrival=False,
    label_i18n="notif.album_reminder.label",
    icon="image-up",
)
register(ALBUM_REMINDER_TYPE)
