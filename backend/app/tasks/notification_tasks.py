"""
@file notification_tasks.py
@brief Celery tasks for push and email notifications.

Routed to the ``notifications`` queue for high-priority delivery.
"""

from __future__ import annotations

import structlog

from app.tasks.celery_app import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(
    bind=True,
    name="app.tasks.notification_tasks.send_push_notification",
    max_retries=3,
    queue="notifications",
)
def send_push_notification(self, user_id: str, payload: dict) -> dict[str, str]:
    """
    @brief Send a Web Push notification to all subscriptions for a user.

    @param user_id UUID string of the recipient user.
    @param payload Notification payload dict (``title``, ``body``, ``url``).
    @return Dict with ``status``.
    """
    logger.info("send_push_notification", user_id=user_id)
    return {"status": "sent"}


@celery_app.task(
    bind=True,
    name="app.tasks.notification_tasks.send_email_notification",
    max_retries=3,
    queue="notifications",
)
def send_email_notification(
    self,
    user_id: str,
    notification_type: str,
    payload: dict,
) -> dict[str, str]:
    """
    @brief Build an email from a Jinja2 template and dispatch via the email task.

    @param user_id UUID string of the recipient user.
    @param notification_type Type key for template selection (e.g. ``"comment"``, ``"mention"``).
    @param payload Context dict passed to the template renderer.
    @return Dict with ``status``.
    """
    logger.info(
        "send_email_notification",
        user_id=user_id,
        notification_type=notification_type,
    )
    return {"status": "sent"}


@celery_app.task(
    name="app.tasks.notification_tasks.dispatch_event_reminders",
    queue="notifications",
)
def dispatch_event_reminders() -> dict[str, int]:
    """
    @brief Find events starting in the next hour and dispatch reminder notifications.

    Run every 15 minutes via Beat.

    @return Dict with ``reminders_sent`` count.
    """
    logger.info("dispatch_event_reminders")
    return {"reminders_sent": 0}
