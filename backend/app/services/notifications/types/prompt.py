"""@file Built-in `prompt` notification type.

@brief Payload schema and registration for `prompt`.
"""

from app.services.notifications.registry import (
    NotificationPayload,
    NotificationType,
    register,
)


class PromptPayload(NotificationPayload):
    """@brief Payload for prompt notifications."""

    prompt_title: str


PROMPT_TYPE = NotificationType(
    key="prompt",
    category="prompt",
    payload_schema=PromptPayload,
    default_channels={"inapp": True, "email": False, "push": True},
    group_window_seconds=None,
    toast_on_arrival=False,
    label_i18n="notifications.types.prompt",
    icon="help-circle",
)
register(PROMPT_TYPE)
