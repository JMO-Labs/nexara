"""@file Web Push notification channel."""

from typing import ClassVar

import structlog

from app.models.notification import Notification
from app.services.notifications.channels.base import ChannelResult
from app.tasks.notification_tasks import send_push_notification

logger = structlog.get_logger(__name__)


class PushChannel:
    """@brief Enqueues Web Push delivery on the Celery broker."""

    key: ClassVar[str] = "push"

    async def send(self, notification: Notification) -> ChannelResult:
        """@brief Enqueue send_push_notification; never raises.

        @param notification The notification to deliver.
        @return ChannelResult(ok=True) or ok=False with error text.
        """
        try:
            send_push_notification.delay(
                str(notification.user_id),
                {
                    "title": notification.type.replace("_", " ").title(),
                    "body": notification.payload.get("message", ""),
                    "url": notification.payload.get("link"),
                },
            )
            return ChannelResult(ok=True)
        except Exception as exc:
            logger.warning(
                "notif.channel.failed",
                channel=self.key,
                notification_id=str(notification.id),
                error=str(exc),
            )
            return ChannelResult(ok=False, error=str(exc))
