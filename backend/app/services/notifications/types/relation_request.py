"""@file Built-in `relation_request` notification type.

@brief Payload schema and registration; accept or decline from the inbox.
"""

from app.services.notifications.registry import (
    Action,
    NotificationPayload,
    NotificationType,
    register,
)


class RelationRequestPayload(NotificationPayload):
    """@brief Payload for relation_request notifications."""

    relation_id: str
    requester_name: str


RELATION_REQUEST_TYPE = NotificationType(
    key="relation_request",
    category="social",
    payload_schema=RelationRequestPayload,
    default_channels={"inapp": True, "email": False, "push": True, "toast": True},
    group_window_seconds=None,
    toast_on_arrival=True,
    actions=(
        Action(
            "accept",
            "notif.relation_request.accept",
            "POST",
            "/api/v1/relations/{relation_id}/confirm",
            "primary",
        ),
        Action(
            "decline",
            "notif.relation_request.decline",
            "DELETE",
            "/api/v1/relations/{relation_id}",
            "neutral",
        ),
    ),
    label_i18n="notif.relation_request.label",
    icon="users",
)
register(RELATION_REQUEST_TYPE)
