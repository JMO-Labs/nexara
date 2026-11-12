"""@file Built-in `event_rsvp` notification type.

@brief Payload schema and registration for `event_rsvp`.
"""

from app.services.notifications.registry import (
    NotificationPayload,
    NotificationType,
    register,
)


class EventRsvpPayload(NotificationPayload):
    """@brief Payload for event_rsvp notifications."""

    actor_name: str
    event_title: str
    status: str


EVENTRSVP_TYPE = NotificationType(
    key="event_rsvp",
    category="event",
    payload_schema=EventRsvpPayload,
    default_channels={"inapp": True, "email": False, "push": False, "toast": False},
    group_window_seconds=600,
    toast_on_arrival=False,
    label_i18n="notif.event_rsvp.label",
    icon="calendar-check",
)
register(EVENTRSVP_TYPE)
