"""@file Built-in `comment` notification type.

@brief Payload schema and registration for `comment`.
"""

from app.services.notifications.registry import (
    NotificationPayload,
    NotificationType,
    register,
)


class CommentPayload(NotificationPayload):
    """@brief Payload for comment notifications."""

    actor_name: str
    excerpt: str | None = None


COMMENT_TYPE = NotificationType(
    key="comment",
    category="social",
    payload_schema=CommentPayload,
    default_channels={"inapp": True, "email": False, "push": False, "toast": True},
    group_window_seconds=300,
    toast_on_arrival=True,
    label_i18n="notif.comment.label",
    icon="message-circle",
)
register(COMMENT_TYPE)
