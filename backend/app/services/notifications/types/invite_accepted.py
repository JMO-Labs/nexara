"""@file Built-in `invite_accepted` notification type.

@brief Payload schema and registration for `invite_accepted`.
"""

from app.services.notifications.registry import (
    NotificationPayload,
    NotificationType,
    register,
)


class InviteAcceptedPayload(NotificationPayload):
    """@brief Payload for invite_accepted notifications."""

    actor_name: str


INVITEACCEPTED_TYPE = NotificationType(
    key="invite_accepted",
    category="social",
    payload_schema=InviteAcceptedPayload,
    default_channels={"inapp": True, "email": False, "push": False},
    group_window_seconds=None,
    toast_on_arrival=False,
    label_i18n="notifications.types.invite_accepted",
    icon="user-plus",
)
register(INVITEACCEPTED_TYPE)
