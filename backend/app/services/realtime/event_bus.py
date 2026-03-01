"""
@file event_bus.py
@brief Singleton EventBus for publishing real-time events.

Replaces the ad-hoc ``feed_publisher`` and ``pubsub_publisher`` callback
patterns with a single injectable dependency.  Services call
``event_bus.emit(event)`` and the bus routes to the correct Valkey
pub/sub channel based on the event's :class:`EventTarget`.

Usage::

    from app.services.realtime.event_bus import event_bus
    from app.services.realtime import events

    await event_bus.emit(events.post_created(community_id, post))
"""

from __future__ import annotations

import structlog

from app.services.realtime.events import (
    CommunityTarget,
    RealtimeEvent,
    UserTarget,
)

logger = structlog.get_logger(__name__)


class EventBus:
    """
    @brief Central dispatcher for real-time events.

    Routes :class:`RealtimeEvent` instances to the appropriate Valkey
    pub/sub channel based on the target type.  Designed to be injected
    into services as a single dependency replacing both
    ``feed_publisher`` and ``pubsub_publisher``.
    """

    async def emit(self, event: RealtimeEvent) -> int:
        """
        @brief Publish an event to the appropriate channel.

        Serialises the event into the wire format ``{type, payload}``
        and delegates to the Valkey pub/sub layer.

        @param event Typed event with target routing info.
        @return Number of Valkey subscribers that received the message.
        """
        from app.services.realtime.pubsub import (
            publish_to_community,
            publish_to_user,
        )

        message = {"type": event.type.value, "payload": event.payload}

        if isinstance(event.target, UserTarget):
            return await publish_to_user(event.target.user_id, message)

        if isinstance(event.target, CommunityTarget):
            return await publish_to_community(
                event.target.community_id, message,
            )

        logger.warning(
            "event_bus_unknown_target",
            target_type=type(event.target).__name__,
        )
        return 0


event_bus = EventBus()
"""@brief Singleton event bus instance shared across the application."""
