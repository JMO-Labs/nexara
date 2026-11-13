"""
@file chat_handler.py
@brief WebSocket inbound handlers for the chat subsystem.

Dispatched from :mod:`app.api.v1.ws` when a frame of type
``chat.message``, ``chat.typing`` or ``chat.read`` arrives.  Keeps the
endpoint itself tiny by delegating to the domain service layer.

All handlers follow the same shape:

  * build a fresh :class:`ChatService` inside a short-lived DB session,
  * validate the inbound payload shape,
  * delegate to the service (which persists + broadcasts via pub/sub),
  * on error, send a ``chat.error`` frame back over the WebSocket.

``chat.typing`` and ``chat.read`` are fire-and-forget broadcasts and do
not touch the DB.  ``chat.message`` persists and also runs link-preview
extraction as a Celery task.
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from fastapi import WebSocket

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.i18n import _
from app.db.session import async_session_factory
from app.repositories.chat_repo import ChatChannelRepository, ChatMessageRepository
from app.repositories.moderation_repo import ModerationRepository
from app.services.chat_service import ChatService, channel_pubsub_name
from app.services.realtime.protocol import OutboundType, build_outbound

logger = structlog.get_logger(__name__)


async def handle_chat_inbound(
    ws: WebSocket,
    user_id: uuid.UUID,
    msg_type: str,
    data: dict[str, Any],
) -> None:
    """
    @brief Route an inbound ``chat.*`` frame to the correct handler.

    @param ws The authenticated WebSocket.
    @param user_id UUID of the sender.
    @param msg_type Inbound frame type (``chat.message`` etc.).
    @param data Parsed JSON dict.
    """
    payload = data.get("payload") or {}

    try:
        if msg_type == "chat.message":
            await _handle_message(ws, user_id, payload)
        elif msg_type == "chat.typing":
            await _handle_typing(user_id, payload)
        elif msg_type == "chat.read":
            await _handle_read(user_id, payload)
        else:
            logger.debug("chat_handler_unknown_type", type=msg_type)
    except AppError as exc:
        await _send_error(ws, exc.code, exc.message)
    except Exception:
        logger.exception("chat_handler_unexpected", type=msg_type, user_id=str(user_id))
        await _send_error(ws, "INTERNAL_ERROR", _("Chat handler failed"))


async def _handle_message(
    ws: WebSocket,
    user_id: uuid.UUID,
    payload: dict[str, Any],
) -> None:
    """@brief Persist a new chat message and let the service broadcast it."""
    channel_id_raw = payload.get("channel_id")
    content = payload.get("content")
    if not channel_id_raw or not isinstance(content, str) or not content.strip():
        await _send_error(ws, "VALIDATION_ERROR", _("Invalid chat message payload"))
        return

    try:
        channel_id = uuid.UUID(str(channel_id_raw))
    except ValueError:
        await _send_error(ws, "VALIDATION_ERROR", _("Invalid channel_id"))
        return

    async with async_session_factory() as session:
        try:
            from sqlalchemy import select

            from app.models.user import User as _UserModel

            result = await session.execute(select(_UserModel).where(_UserModel.id == user_id))
            user = result.scalar_one_or_none()
            if user is None:
                await _send_error(ws, "AUTHENTICATION_ERROR", _("User not found"))
                return

            settings = get_settings()
            community_id = uuid.UUID(settings.COMMUNITY_ID)
            service = ChatService(
                channel_repo=ChatChannelRepository(session),
                message_repo=ChatMessageRepository(session),
                community_id=community_id,
                rate_limiter=_maybe_rate_limiter(),
                moderation_repo=ModerationRepository(session),
            )
            await service.send_message(user, channel_id, content)
            await session.commit()
        except AppError:
            await session.rollback()
            raise
        except Exception:
            await session.rollback()
            raise


async def _handle_typing(user_id: uuid.UUID, payload: dict[str, Any]) -> None:
    """@brief Broadcast a typing indicator on the chat channel (no persistence)."""
    channel_id_raw = payload.get("channel_id")
    if not channel_id_raw:
        return
    try:
        channel_id = uuid.UUID(str(channel_id_raw))
    except ValueError:
        return

    from app.services.realtime.pubsub import publish

    await publish(
        channel_pubsub_name(channel_id),
        {
            "type": "chat.typing",
            "payload": {
                "channel_id": str(channel_id),
                "user_id": str(user_id),
            },
        },
    )


async def _handle_read(user_id: uuid.UUID, payload: dict[str, Any]) -> None:
    """@brief Broadcast a read-receipt envelope for the given message."""
    channel_id_raw = payload.get("channel_id")
    message_id_raw = payload.get("message_id")
    if not channel_id_raw or not message_id_raw:
        return
    try:
        channel_id = uuid.UUID(str(channel_id_raw))
        message_id = uuid.UUID(str(message_id_raw))
    except ValueError:
        return

    from app.services.realtime.pubsub import publish

    await publish(
        channel_pubsub_name(channel_id),
        {
            "type": "chat.read",
            "payload": {
                "channel_id": str(channel_id),
                "message_id": str(message_id),
                "user_id": str(user_id),
            },
        },
    )


async def _send_error(ws: WebSocket, code: str, message: str) -> None:
    """@brief Send a ``chat.error`` envelope to the WebSocket, swallowing send errors."""
    try:
        await ws.send_text(
            build_outbound(OutboundType.CHAT_ERROR, {"code": code, "message": message})
        )
    except Exception:
        logger.debug("chat_handler_send_error_failed", exc_info=True)


def _maybe_rate_limiter() -> Any:
    """@brief Return the Valkey cache pool for rate-limit counters (or None)."""
    try:
        from app.core.valkey import DB_CACHE, get_pool

        return get_pool(get_settings(), DB_CACHE)
    except Exception:
        return None
