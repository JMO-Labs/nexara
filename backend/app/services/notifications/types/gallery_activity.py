"""@file Built-in `gallery_activity` notification type.

@brief Payload schema and registration for `gallery_activity`.
"""

from app.services.notifications.registry import (
    NotificationPayload,
    NotificationType,
    register,
)


class GalleryActivityPayload(NotificationPayload):
    """@brief Payload for gallery_activity notifications."""

    actor_name: str
    gallery_title: str
    activity: str


GALLERYACTIVITY_TYPE = NotificationType(
    key="gallery_activity",
    category="gallery",
    payload_schema=GalleryActivityPayload,
    default_channels={"inapp": True, "email": False, "push": False, "toast": False},
    group_window_seconds=900,
    toast_on_arrival=False,
    label_i18n="notif.gallery_activity.label",
    icon="images",
)
register(GALLERYACTIVITY_TYPE)
