"""@file Built-in `reaction` notification type.

@brief Payload schema and registration for `reaction`.
"""

from app.services.notifications.registry import (
    NotificationPayload,
    NotificationType,
    register,
)


class ReactionPayload(NotificationPayload):
    """@brief Payload for reaction notifications."""

    actor_name: str
    emoji: str
    excerpt: str


REACTION_TYPE = NotificationType(
    key="reaction",
    category="social",
    payload_schema=ReactionPayload,
    default_channels={"inapp": True, "email": False, "push": False, "toast": False},
    group_window_seconds=600,
    toast_on_arrival=False,
    label_i18n="notif.reaction.label",
    icon="smile",
)
register(REACTION_TYPE)
