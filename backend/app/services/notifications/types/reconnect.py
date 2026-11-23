"""@file Built-in `reconnect` notification type.

@brief Private nudge to reach out to a relative; Message (item link) or snooze.
"""

from app.services.notifications.registry import (
    Action,
    NotificationPayload,
    NotificationType,
    register,
)


class ReconnectPayload(NotificationPayload):
    """@brief Payload for reconnect notifications (``link`` opens the DM)."""

    target_name: str


RECONNECT_TYPE = NotificationType(
    key="reconnect",
    category="social",
    payload_schema=ReconnectPayload,
    default_channels={"inapp": True, "email": False, "push": False, "toast": False},
    group_window_seconds=None,
    label_i18n="notif.reconnect.label",
    icon="heart-handshake",
    actions=(
        Action(
            "snooze",
            "notif.reconnect.snooze",
            "POST",
            "/api/v1/reconnect/snooze?target_id={target_id}",
            "neutral",
        ),
    ),
)
register(RECONNECT_TYPE)
