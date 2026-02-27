"""
@file sse.py
@brief Server-Sent Events endpoint for notifications and feed updates.

Uses standard HTTP Bearer authentication (unlike WebSocket, which uses
first-message auth).  The SSE stream delivers:
  - ``notification`` events for in-app notifications
  - ``feed_update`` events for new posts, comments, reactions
  - ``: heartbeat`` comments every 15 seconds to keep the connection alive

Clients reconnect with ``Last-Event-ID`` to receive missed events.
"""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.services.realtime.connection_manager import SSEConnection, manager
from app.services.realtime.presence import set_offline, set_online
from app.services.realtime.protocol import build_sse_event

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["realtime"])

HEARTBEAT_INTERVAL_SECONDS = 15
"""@brief Interval between SSE heartbeat comments."""


@router.get("/notifications/stream")
async def notification_stream(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> StreamingResponse:
    """
    @brief Open an SSE stream for the authenticated user.

    The response uses ``text/event-stream`` content type.  Events are
    pushed via the :class:`ConnectionManager` and consumed from the
    :class:`SSEConnection` queue.
    """
    sse_conn = SSEConnection(user.id)
    last_event_id = request.headers.get("Last-Event-ID")

    return StreamingResponse(
        _event_generator(sse_conn, user.id, last_event_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _event_generator(
    conn: SSEConnection,
    user_id: UUID,
    last_event_id: str | None,
) -> Any:
    """
    @brief Async generator that yields SSE-formatted strings.

    Registers with the connection manager on start, deregisters on stop.
    Interleaves heartbeat comments between queued messages.

    @param conn SSE connection wrapper with a message queue.
    @param user_id Authenticated user UUID.
    @param last_event_id Client's Last-Event-ID for missed-event recovery.
    """
    await manager.connect(conn, user_id, is_sse=True)
    await set_online(user_id)

    event_counter = 0

    try:
        if last_event_id:
            logger.info(
                "sse_reconnect",
                user_id=str(user_id),
                last_event_id=last_event_id,
            )

        while True:
            try:
                message = await asyncio.wait_for(
                    conn.queue.get(), timeout=HEARTBEAT_INTERVAL_SECONDS,
                )
                event_counter += 1
                event_type = message.get("type", "notification")
                event_id = str(event_counter)
                yield build_sse_event(
                    event=event_type,
                    data=message.get("payload", message),
                    event_id=event_id,
                )
            except TimeoutError:
                yield ": heartbeat\n\n"

    except asyncio.CancelledError:
        logger.debug("sse_cancelled", user_id=str(user_id))
    except Exception:
        logger.exception("sse_error", user_id=str(user_id))
    finally:
        await manager.disconnect(conn, user_id, is_sse=True)
        await set_offline(user_id)
