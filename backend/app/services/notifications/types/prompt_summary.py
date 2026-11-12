"""@file Built-in `prompt_summary` notification type.

@brief Payload schema and registration for `prompt_summary`.
"""

from app.services.notifications.registry import (
    NotificationPayload,
    NotificationType,
    register,
)


class PromptSummaryPayload(NotificationPayload):
    """@brief Payload for prompt_summary notifications."""

    response_count: int


PROMPTSUMMARY_TYPE = NotificationType(
    key="prompt_summary",
    category="prompt",
    payload_schema=PromptSummaryPayload,
    default_channels={"inapp": True, "email": False, "push": False},
    group_window_seconds=None,
    toast_on_arrival=False,
    label_i18n="notifications.types.prompt_summary",
    icon="list-checks",
)
register(PROMPTSUMMARY_TYPE)
