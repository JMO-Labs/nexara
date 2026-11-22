"""@file Built-in `ride_update` notification type.

@brief Payload schema and registration for `ride_update`.
"""

from app.services.notifications.registry import (
    NotificationPayload,
    NotificationType,
    register,
)


class RideUpdatePayload(NotificationPayload):
    """@brief Payload for ride_update notifications."""

    ride_id: str
    event_id: str
    event_title: str
    action: str


RIDE_UPDATE_TYPE = NotificationType(
    key="ride_update",
    category="social",
    payload_schema=RideUpdatePayload,
    default_channels={"inapp": True, "email": False, "push": True, "toast": False},
    group_window_seconds=None,
    toast_on_arrival=False,
    label_i18n="notif.ride_update.label",
    icon="car",
)
register(RIDE_UPDATE_TYPE)
