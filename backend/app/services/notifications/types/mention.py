"""@file Built-in `mention` notification type.

@brief Payload schema and registration for `mention`.
"""

from app.services.notifications.registry import (
    NotificationPayload,
    NotificationType,
    register,
)


class MentionPayload(NotificationPayload):
    """@brief Payload for mention notifications."""

    actor_name: str
    excerpt: str | None = None


MENTION_TYPE = NotificationType(
    key="mention",
    category="social",
    payload_schema=MentionPayload,
    default_channels={"inapp": True, "email": True, "push": True, "toast": True},
    group_window_seconds=None,
    toast_on_arrival=True,
    label_i18n="notif.mention.label",
    icon="at-sign",
)
register(MENTION_TYPE)
