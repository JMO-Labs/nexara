"""@file Notification registry package.

@brief Re-exports the registry public API.
"""

from app.services.notifications.registry import (
    _REGISTRY,
    Action,
    Category,
    Channel,
    NotificationPayload,
    NotificationType,
    get,
    iter_types,
    register,
    to_json_schema,
)

__all__ = [
    "_REGISTRY",
    "Action",
    "Category",
    "Channel",
    "NotificationPayload",
    "NotificationType",
    "get",
    "iter_types",
    "register",
    "to_json_schema",
]
