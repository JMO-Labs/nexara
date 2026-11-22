"""@file Built-in `list_assigned` notification type.

@brief Payload schema and registration for `list_assigned` (assign/accept/decline).
"""

from app.services.notifications.registry import (
    NotificationPayload,
    NotificationType,
    register,
)


class ListAssignedPayload(NotificationPayload):
    """@brief Payload for list_assigned notifications."""

    list_id: str
    item_id: str
    item_title: str
    event: str


LISTASSIGNED_TYPE = NotificationType(
    key="list_assigned",
    category="list",
    payload_schema=ListAssignedPayload,
    default_channels={"inapp": True, "email": False, "push": False, "toast": False},
    toast_on_arrival=False,
    label_i18n="notif.list_assigned.label",
    icon="user-check",
)
register(LISTASSIGNED_TYPE)
