"""
@file activity_publish.py
@brief Record an activity and ping the audience's home feeds.
"""

from __future__ import annotations

from typing import Any

import structlog

from app.models.activity_event import ActivityEvent
from app.repositories.activity_repo import ActivityRepository
from app.services.realtime.audience import emit_to_audience, resolve_audience
from app.services.realtime.events import EventType

logger = structlog.get_logger(__name__)


async def record_activity(
    activity_repo: ActivityRepository,
    session: Any,
    event_bus: Any,
    **record_kwargs: Any,
) -> ActivityEvent | None:
    """
    @brief Record an activity, then emit ``feed_ping`` to its audience.

    Emission failure is logged, never raised.

    @param activity_repo Activity repository.
    @param session DB session for audience resolution.
    @param event_bus EventBus; ``None`` uses the shared singleton.
    @param record_kwargs Keyword args for ``ActivityRepository.record``.
    @return The recorded event, or None if the best-effort insert failed.
    """
    event = await activity_repo.record(**record_kwargs)
    if event is None:
        return None
    try:
        if event_bus is None:
            from app.services.realtime.event_bus import event_bus as shared

            event_bus = shared
        audience = await resolve_audience(
            session,
            record_kwargs["community_id"],
            visibility=record_kwargs["visibility"],
            subgroup_id=record_kwargs.get("subgroup_id"),
            author_id=record_kwargs["actor_id"],
        )
        await emit_to_audience(
            event_bus, audience, EventType.FEED_PING, {"at": event.created_at.isoformat()}
        )
    except Exception:
        logger.exception("feed_ping_failed", verb=record_kwargs.get("verb"))
    return event
