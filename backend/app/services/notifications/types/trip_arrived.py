"""@file Built-in `trip_arrived` notification type.

@brief Registration for `trip_arrived` (safe arrival).
"""

from app.services.notifications.registry import NotificationType, register
from app.services.notifications.types._trip import TripPayload

TRIP_ARRIVED_TYPE = NotificationType(
    key="trip_arrived",
    category="social",
    payload_schema=TripPayload,
    default_channels={"inapp": True, "email": False, "push": True, "toast": False},
    group_window_seconds=None,
    toast_on_arrival=False,
    digestable=False,
    label_i18n="notif.trip_arrived.label",
    icon="house",
)
register(TRIP_ARRIVED_TYPE)
