"""@file Email notification channel (Celery delegation)."""

from typing import ClassVar

import structlog

from app.models.notification import Notification
from app.services.notifications.channels.base import ChannelResult
from app.tasks.notification_tasks import send_email_notification

logger = structlog.get_logger(__name__)


class EmailChannel:
    """@brief Enqueues the existing email Celery task for a notification."""

    key: ClassVar[str] = "email"

    async def send(self, notification: Notification) -> ChannelResult:
        """@brief Enqueue send_email_notification; never raises.

        @param notification The notification to deliver.
        @return ChannelResult(ok=True) or ok=False with error text.
        """
        try:
            actor_ids = getattr(notification, "actor_ids", None) or []
            send_email_notification.delay(
                str(notification.user_id),
                notification.type,
                {**notification.payload, "actor_ids": [str(a) for a in actor_ids]},
            )
            return ChannelResult(ok=True)
        except Exception as exc:
            logger.warning(
                "notif.channel.failed",
                channel=self.key,
                type_key=notification.type,
                user_id=str(notification.user_id),
                error=str(exc),
            )
            return ChannelResult(ok=False, error=str(exc))
