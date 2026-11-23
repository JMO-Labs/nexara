"""@file Built-in `story_answered` notification type.

@brief Someone answered the story you asked for.
"""

from app.services.notifications.registry import (
    NotificationPayload,
    NotificationType,
    register,
)


class StoryAnsweredPayload(NotificationPayload):
    """@brief Payload for story_answered notifications."""

    request_id: str
    post_id: str
    question: str
    teller_name: str


STORY_ANSWERED_TYPE = NotificationType(
    key="story_answered",
    category="social",
    payload_schema=StoryAnsweredPayload,
    default_channels={"inapp": True, "email": False, "push": True, "toast": True},
    group_window_seconds=None,
    toast_on_arrival=True,
    label_i18n="notif.story_answered.label",
    icon="mic",
)
register(STORY_ANSWERED_TYPE)
