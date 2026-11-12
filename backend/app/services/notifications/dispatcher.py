"""@file Notification dispatcher.

@brief Parallel, failure-isolated fanout to enabled delivery channels.
"""

import asyncio

import structlog

from app.models.notification import Notification
from app.services.notifications.channels.apprise import AppriseChannel
from app.services.notifications.channels.base import Channel, ChannelResult
from app.services.notifications.channels.email import EmailChannel
from app.services.notifications.channels.inapp import InAppChannel
from app.services.notifications.channels.push import PushChannel
from app.services.notifications.registry import NotificationType
from app.services.realtime.event_bus import EventBus

logger = structlog.get_logger(__name__)


class Dispatcher:
    """@brief Orchestrates notification delivery across channels."""

    def __init__(self, event_bus: EventBus) -> None:
        """@param event_bus Bus passed to the in-app channel."""
        self._channels: dict[str, Channel] = {}
        self._bus = event_bus
        self.register_channel(InAppChannel(event_bus))
        self.register_channel(EmailChannel())
        self.register_channel(PushChannel())
        self.register_channel(AppriseChannel())

    def register_channel(self, ch: Channel) -> None:
        """@param ch Channel to register under its key."""
        self._channels[ch.key] = ch

    async def dispatch(
        self,
        notification: Notification,
        type: NotificationType,  # noqa: A002
        effective_channels: dict[str, bool],
    ) -> list[ChannelResult]:
        """@brief Send to every enabled, registered channel in parallel.

        @param notification The notification to deliver.
        @param type Its notification type.
        @param effective_channels Channel key -> enabled after preference gating.
        @return One ChannelResult per attempted channel; never raises.
        """
        keys = [k for k, on in effective_channels.items() if on and k in self._channels]
        raw = await asyncio.gather(
            *(self._channels[k].send(notification) for k in keys),
            return_exceptions=True,
        )
        results: list[ChannelResult] = []
        for key, r in zip(keys, raw, strict=True):
            res = r if isinstance(r, ChannelResult) else ChannelResult(ok=False, error=str(r))
            if res.ok:
                logger.info("notification_channel_sent", channel=key, type=type.key)
            else:
                logger.warning(
                    "notification_channel_failed",
                    channel=key,
                    type=type.key,
                    error=res.error,
                    skipped_reason=res.skipped_reason,
                )
            results.append(res)
        return results
