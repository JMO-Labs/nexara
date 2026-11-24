"""@file Web Push notification channel."""

from typing import Any, ClassVar

import structlog

from app.models.notification import Notification
from app.services.notifications.channels.base import ChannelResult
from app.tasks.notification_tasks import send_push_notification

logger = structlog.get_logger(__name__)


_THREAD_KEYS = ("post_id", "channel_id", "event_id", "target_id")


def build_push_payload(notification: Notification) -> dict[str, Any]:
    """@brief Build the push payload from the same text the in-app list shows.

    Title is the actor name (body is the message minus that prefix); without
    an actor the title is the type label. ``tag`` stacks per thread.

    @param notification The notification to render.
    @return Dict with title, body, url, tag.
    """
    p = notification.payload or {}
    message = str(p.get("message") or "")
    actor = p.get("actor_name")
    if actor and isinstance(actor, str):
        title = actor
        body = message.removeprefix(actor).strip() or message
    else:
        title = notification.type.replace("_", " ").title()
        body = message
    thread = next((str(p[k]) for k in _THREAD_KEYS if p.get(k)), None)
    tag = f"{notification.type}:{thread}" if thread else notification.type
    return {"title": title, "body": body, "url": p.get("link"), "tag": tag}


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
                build_push_payload(notification),
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
