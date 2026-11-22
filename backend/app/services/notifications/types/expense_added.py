"""@file Built-in `expense_added` notification type.

@brief Payload schema and registration for `expense_added`.
"""

from app.services.notifications.registry import (
    NotificationPayload,
    NotificationType,
    register,
)


class ExpenseAddedPayload(NotificationPayload):
    """@brief Payload for expense_added notifications."""

    ledger_id: str
    ledger_name: str
    actor_name: str


EXPENSE_ADDED_TYPE = NotificationType(
    key="expense_added",
    category="social",
    payload_schema=ExpenseAddedPayload,
    default_channels={"inapp": True, "email": False, "push": True, "toast": False},
    group_window_seconds=None,
    toast_on_arrival=False,
    label_i18n="notif.expense_added.label",
    icon="receipt",
)
register(EXPENSE_ADDED_TYPE)
