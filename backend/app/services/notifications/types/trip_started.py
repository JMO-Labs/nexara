"""@file Built-in `trip_started` notification type.

@brief Registration for `trip_started` (safe arrival).
"""

from app.services.notifications.registry import NotificationType, register
from app.services.notifications.types._trip import TripPayload

TRIP_STARTED_TYPE = NotificationType(
    key="trip_started",
    category="social",
    payload_schema=TripPayload,
    default_channels={"inapp": True, "email": False, "push": True, "toast": False},
    group_window_seconds=None,
    toast_on_arrival=False,
    digestable=False,
    label_i18n="notif.trip_started.label",
    icon="route",
)
register(TRIP_STARTED_TYPE)
