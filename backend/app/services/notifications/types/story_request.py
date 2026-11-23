"""@file Built-in `story_request` notification type.

@brief Someone asked you to tell a story (also used for the day-14 reminder).
"""

from app.services.notifications.registry import (
    NotificationPayload,
    NotificationType,
    register,
)


class StoryRequestPayload(NotificationPayload):
    """@brief Payload for story_request notifications."""

    request_id: str
    question: str
    asker_name: str


STORY_REQUEST_TYPE = NotificationType(
    key="story_request",
    category="social",
    payload_schema=StoryRequestPayload,
    default_channels={"inapp": True, "email": False, "push": True, "toast": True},
    group_window_seconds=None,
    toast_on_arrival=True,
    label_i18n="notif.story_request.label",
    icon="mic",
)
register(STORY_REQUEST_TYPE)
