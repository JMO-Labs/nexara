"""@file Built-in `list_signup` notification type.

@brief Payload schema and registration for `list_signup`.
"""

from app.services.notifications.registry import (
    NotificationPayload,
    NotificationType,
    register,
)


class ListSignupPayload(NotificationPayload):
    """@brief Payload for list_signup notifications."""

    list_id: str
    item_id: str
    item_title: str
    claimer_id: str
    claimer_name: str
    quantity: int


LISTSIGNUP_TYPE = NotificationType(
    key="list_signup",
    category="list",
    payload_schema=ListSignupPayload,
    default_channels={"inapp": True, "email": False, "push": False, "toast": False},
    group_window_seconds=600,
    toast_on_arrival=False,
    label_i18n="notif.list_signup.label",
    icon="hand",
)
register(LISTSIGNUP_TYPE)
