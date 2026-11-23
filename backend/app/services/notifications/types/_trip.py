"""@file Shared payload for the trip_* notification types.

@brief One payload model reused by trip_started, trip_overdue and trip_arrived.
"""

from app.services.notifications.registry import NotificationPayload


class TripPayload(NotificationPayload):
    """@brief Payload for safe-arrival notifications (never carries a location)."""

    trip_id: str
    label: str
    traveler_name: str
