"""@file Built-in `list_item` notification type.

@brief Payload schema and registration for `list_item`.
"""

from app.services.notifications.registry import (
    NotificationPayload,
    NotificationType,
    register,
)


class ListItemPayload(NotificationPayload):
    """@brief Payload for list_item notifications."""

    list_id: str
    item_id: str
    item_title: str
    adder_id: str


LISTITEM_TYPE = NotificationType(
    key="list_item",
    category="list",
    payload_schema=ListItemPayload,
    default_channels={"inapp": True, "email": False, "push": False, "toast": False},
    group_window_seconds=600,
    toast_on_arrival=False,
    label_i18n="notif.list_item.label",
    icon="list-plus",
)
register(LISTITEM_TYPE)
