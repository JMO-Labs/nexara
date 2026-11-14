"""@file Webhook notification channel.

@brief Fans a notification out to every matching, enabled webhook
subscription by enqueuing one ``webhook_deliver`` Celery task each.
"""

from typing import ClassVar

import structlog

from app.models.notification import Notification
from app.repositories.webhook_repo import WebhookRepository
from app.services.notifications.channels.base import ChannelResult
from app.tasks.notification_tasks import webhook_deliver

logger = structlog.get_logger(__name__)


class WebhookChannel:
    """@brief Enqueues signed webhook deliveries; never raises."""

    key: ClassVar[str] = "webhook"

    def __init__(self, repo: WebhookRepository) -> None:
        """@param repo DB-bound webhook repository."""
        self._repo = repo

    async def send(self, notification: Notification) -> ChannelResult:
        """@brief Enqueue one delivery per matching subscription.

        A failure to enqueue one subscription does not block the others.

        @param notification The notification to deliver.
        @return ok when at least one task was enqueued, skipped when nothing
            matches, ok=False with error otherwise.
        """
        try:
            subs = await self._repo.list_matching(
                notification.community_id, notification.user_id, notification.type
            )
        except Exception as exc:
            return self._failed(notification, exc)
        if not subs:
            return ChannelResult(ok=True, skipped_reason="no_subscriptions")
        enqueued = 0
        last_exc: Exception | None = None
        for sub in subs:
            try:
                webhook_deliver.delay(str(sub.id), str(notification.id))
                enqueued += 1
            except Exception as exc:
                last_exc = exc
                self._failed(notification, exc, webhook_id=str(sub.id))
        if enqueued:
            return ChannelResult(ok=True)
        return ChannelResult(ok=False, error=str(last_exc))

    def _failed(self, notification: Notification, exc: Exception, **extra: str) -> ChannelResult:
        """@brief Log ``notif.channel.failed`` and build a failed result."""
        logger.warning(
            "notif.channel.failed",
            channel=self.key,
            notification_id=str(notification.id),
            error=str(exc),
            **extra,
        )
        return ChannelResult(ok=False, error=str(exc))
