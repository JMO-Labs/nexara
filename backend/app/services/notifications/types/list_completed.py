"""@file Built-in `list_completed` notification type.

@brief Payload schema and registration for `list_completed`.
"""

from app.services.notifications.registry import (
    NotificationPayload,
    NotificationType,
    register,
)


class ListCompletedPayload(NotificationPayload):
    """@brief Payload for list_completed notifications."""

    list_id: str
    item_id: str
    item_title: str
    completer_id: str
    list_title: str | None = None
    completion_mode: str | None = None


LISTCOMPLETED_TYPE = NotificationType(
    key="list_completed",
    category="list",
    payload_schema=ListCompletedPayload,
    default_channels={"inapp": True, "email": False, "push": False, "toast": False},
    group_window_seconds=600,
    toast_on_arrival=False,
    label_i18n="notif.list_completed.label",
    icon="list-checks",
)
register(LISTCOMPLETED_TYPE)
