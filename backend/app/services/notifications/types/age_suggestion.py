"""@file Built-in `age_suggestion` notification type.

@brief Admin-only notice that a member suggested an age group for someone.
"""

from app.services.notifications.registry import (
    NotificationPayload,
    NotificationType,
    register,
)


class AgeSuggestionPayload(NotificationPayload):
    """@brief Payload for age_suggestion notifications."""


AGESUGGESTION_TYPE = NotificationType(
    key="age_suggestion",
    category="system",
    payload_schema=AgeSuggestionPayload,
    default_channels={"inapp": True, "email": False, "push": False, "toast": False},
    label_i18n="notif.age_suggestion.label",
    icon="users",
)
register(AGESUGGESTION_TYPE)
