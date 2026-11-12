"""@file Built-in `new_post` notification type.

@brief Payload schema and registration for `new_post`.
"""

from app.services.notifications.registry import (
    NotificationPayload,
    NotificationType,
    register,
)


class NewPostPayload(NotificationPayload):
    """@brief Payload for new_post notifications."""

    actor_name: str
    title: str


NEWPOST_TYPE = NotificationType(
    key="new_post",
    category="social",
    payload_schema=NewPostPayload,
    default_channels={"inapp": True, "email": False, "push": False, "toast": False},
    group_window_seconds=900,
    toast_on_arrival=False,
    label_i18n="notif.new_post.label",
    icon="file-text",
)
register(NEWPOST_TYPE)
