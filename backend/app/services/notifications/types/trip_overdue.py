"""@file Built-in `trip_overdue` notification type.

@brief Registration for `trip_overdue` (safe arrival).
"""

from app.services.notifications.registry import NotificationType, register
from app.services.notifications.types._trip import TripPayload

TRIP_OVERDUE_TYPE = NotificationType(
    key="trip_overdue",
    category="social",
    payload_schema=TripPayload,
    default_channels={"inapp": True, "email": False, "push": True, "toast": True},
    group_window_seconds=None,
    toast_on_arrival=True,
    digestable=False,
    bypass_dnd=True,  # safety alert: someone may be in trouble
    label_i18n="notif.trip_overdue.label",
    icon="siren",
)
register(TRIP_OVERDUE_TYPE)
