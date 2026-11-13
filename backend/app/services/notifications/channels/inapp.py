"""@file In-app (SSE/WS) notification channel."""

from typing import ClassVar

import structlog

from app.models.notification import Notification
from app.services.notifications.channels.base import ChannelResult
from app.services.realtime import events
from app.services.realtime.event_bus import EventBus

logger = structlog.get_logger(__name__)


class InAppChannel:
    """@brief Pushes notifications to the user's live connections."""

    key: ClassVar[str] = "inapp"

    def __init__(self, event_bus: EventBus) -> None:
        """@param event_bus Bus used to fan out realtime events."""
        self._bus = event_bus

    async def send(self, notification: Notification) -> ChannelResult:
        """@brief Emit a user_notification event; never raises.

        @param notification The notification to deliver.
        @return ChannelResult(ok=True) or ok=False with error text.
        """
        try:
            await self._bus.emit(
                events.user_notification(
                    user_id=notification.user_id,
                    notification_id=notification.id,
                    notification_type=notification.type,
                    payload=notification.payload,
                    created_at=notification.created_at.isoformat(),
                    updated_at=(
                        notification.updated_at.isoformat() if notification.updated_at else None
                    ),
                    count=notification.count or 1,
                    actor_ids=notification.actor_ids or [],
                )
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
