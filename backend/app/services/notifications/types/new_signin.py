"""@file Built-in `new_signin` notification type.

@brief Alert sent when an account signs in from a device not seen in 90 days.
"""

from app.services.notifications.registry import (
    NotificationPayload,
    NotificationType,
    register,
)


class NewSigninPayload(NotificationPayload):
    """@brief Payload: ``message`` plus the device label and client IP."""

    device: str
    ip: str | None = None


NEW_SIGNIN_TYPE = NotificationType(
    key="new_signin",
    category="system",
    payload_schema=NewSigninPayload,
    default_channels={"inapp": True, "email": True, "push": False, "toast": False},
    group_window_seconds=None,
    bypass_dnd=True,
    digestable=False,
    label_i18n="notif.new_signin.label",
    icon="shield-alert",
)
register(NEW_SIGNIN_TYPE)
