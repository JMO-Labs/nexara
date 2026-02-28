"""
@file ws.py
@brief WebSocket endpoint with first-message JWT authentication.

The client opens a WebSocket to ``/ws/`` and **must** send an auth message
as the first frame within 10 seconds::

    { "type": "auth", "payload": { "token": "<JWT>" } }

After authentication, the server responds with ``auth_ok`` and begins
relaying messages.  An unauthenticated connection is closed with code 4001.
"""

from __future__ import annotations

import asyncio
import json
from uuid import UUID

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from app.core.i18n import _
from app.core.security import decode_token
from app.services.realtime.connection_manager import manager
from app.services.realtime.presence import set_offline, set_online
from app.services.realtime.protocol import (
    InboundType,
    OutboundType,
    build_outbound,
)

logger = structlog.get_logger(__name__)

router = APIRouter()

AUTH_TIMEOUT_SECONDS = 10
"""@brief Maximum time to wait for the first auth message before closing."""

HEARTBEAT_INTERVAL_SECONDS = 30
"""@brief Interval for ping/pong heartbeat checks."""


@router.websocket("/ws/")
async def websocket_endpoint(ws: WebSocket) -> None:
    """
    @brief Accept a WebSocket connection and handle the auth + message loop.

    Close codes:
      - 4001: Authentication failed or timed out.
      - 4002: Invalid message format.
      - 1000: Normal closure.
    """
    await ws.accept()

    user_id = await _authenticate(ws)
    if user_id is None:
        return

    await manager.connect(ws, user_id, is_sse=False)
    await set_online(user_id)

    try:
        await _message_loop(ws, user_id)
    except WebSocketDisconnect:
        logger.debug("ws_client_disconnected", user_id=str(user_id))
    except Exception:
        logger.exception("ws_unexpected_error", user_id=str(user_id))
    finally:
        await manager.disconnect(ws, user_id, is_sse=False)
        await set_offline(user_id)


async def _authenticate(ws: WebSocket) -> UUID | None:
    """
    @brief Wait for the first auth message and validate the JWT.

    @param ws The accepted WebSocket.
    @return The authenticated user UUID, or None if auth failed.
    """
    try:
        raw = await asyncio.wait_for(ws.receive_text(), timeout=AUTH_TIMEOUT_SECONDS)
    except TimeoutError:
        logger.warning("ws_auth_timeout")
        await _close_safe(ws, 4001, _("Authentication timeout"))
        return None
    except WebSocketDisconnect:
        return None

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        await _close_safe(ws, 4002, _("Invalid JSON"))
        return None

    if data.get("type") != InboundType.AUTH:
        await _close_safe(ws, 4001, _("First message must be auth"))
        return None

    token = data.get("payload", {}).get("token")
    if not token:
        error_msg = build_outbound(OutboundType.AUTH_ERROR, {"message": _("Token missing")})
        await ws.send_text(error_msg)
        await _close_safe(ws, 4001, _("Token missing"))
        return None

    try:
        payload = decode_token(token, expected_type="access")
        user_id = UUID(payload["sub"])
    except (ValueError, KeyError):
        error_msg = build_outbound(OutboundType.AUTH_ERROR, {"message": _("Invalid token")})
        await ws.send_text(error_msg)
        await _close_safe(ws, 4001, _("Invalid token"))
        return None

    ok_msg = build_outbound(OutboundType.AUTH_OK, {"user_id": str(user_id)})
    await ws.send_text(ok_msg)
    logger.info("ws_authenticated", user_id=str(user_id))
    return user_id


async def _message_loop(ws: WebSocket, user_id: UUID) -> None:
    """
    @brief Read messages from the client and dispatch to handlers.

    @param ws The authenticated WebSocket.
    @param user_id UUID of the authenticated user.
    """
    while True:
        raw = await ws.receive_text()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue

        msg_type = data.get("type")

        if msg_type == InboundType.PING:
            pong = build_outbound(OutboundType.PONG)
            await ws.send_text(pong)
            await set_online(user_id)

        elif msg_type == InboundType.TYPING:
            from app.services.realtime.pubsub import publish_to_community

            await publish_to_community(
                UUID("00000000-0000-0000-0000-000000000001"),
                {
                    "type": OutboundType.TYPING,
                    "payload": {"user_id": str(user_id)},
                },
            )
        else:
            logger.debug("ws_unknown_message_type", type=msg_type, user_id=str(user_id))


async def _close_safe(ws: WebSocket, code: int, reason: str) -> None:
    """@brief Close the WebSocket if it's still open, ignoring errors."""
    try:
        if ws.client_state == WebSocketState.CONNECTED:
            await ws.close(code=code, reason=reason)
    except Exception:
        pass
