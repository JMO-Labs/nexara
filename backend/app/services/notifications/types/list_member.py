"""@file Built-in `list_member` notification type.

@brief Payload schema and registration for `list_member`.
"""

from app.services.notifications.registry import (
    NotificationPayload,
    NotificationType,
    register,
)


class ListMemberPayload(NotificationPayload):
    """@brief Payload for list_member notifications."""

    list_id: str
    list_title: str
    inviter_id: str
    invitee_id: str


LISTMEMBER_TYPE = NotificationType(
    key="list_member",
    category="list",
    payload_schema=ListMemberPayload,
    default_channels={"inapp": True, "email": True, "push": False, "toast": False},
    toast_on_arrival=False,
    label_i18n="notif.list_member.label",
    icon="user-plus",
)
register(LISTMEMBER_TYPE)
