"""@file Built-in `gallery_reminder` notification type.

@brief Payload schema and registration for `gallery_reminder`.
"""

from app.services.notifications.registry import (
    NotificationPayload,
    NotificationType,
    register,
)


class GalleryReminderPayload(NotificationPayload):
    """@brief Payload for gallery_reminder notifications."""

    gallery_title: str


GALLERYREMINDER_TYPE = NotificationType(
    key="gallery_reminder",
    category="gallery",
    payload_schema=GalleryReminderPayload,
    default_channels={"inapp": True, "email": False, "push": True},
    group_window_seconds=None,
    toast_on_arrival=False,
    label_i18n="notifications.types.gallery_reminder",
    icon="image-up",
)
register(GALLERYREMINDER_TYPE)
