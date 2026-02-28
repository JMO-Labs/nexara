"""
@file protocol.py
@brief Message protocol definitions for WebSocket and SSE transports.

Defines typed message envelopes for all realtime communication.
Every message has a ``type``, ``payload``, and ``ts`` (ISO 8601 timestamp).
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class InboundType(StrEnum):
    """@brief Message types sent from client to server."""

    AUTH = "auth"
    PING = "ping"
    TYPING = "typing"


class OutboundType(StrEnum):
    """@brief Message types sent from server to client."""

    AUTH_OK = "auth_ok"
    AUTH_ERROR = "auth_error"
    PONG = "pong"
    NOTIFICATION = "notification"
    FEED_UPDATE = "feed_update"
    PRESENCE = "presence"
    TYPING = "typing"


class BaseMessage(BaseModel):
    """
    @brief Base envelope for all realtime messages.

    @param type Message type identifier.
    @param payload Arbitrary JSON payload.
    @param ts ISO 8601 timestamp of when the message was created.
    """

    type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    ts: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


# ── Inbound messages (client → server) ───────────────────────────────────


class AuthMessage(BaseModel):
    """@brief First message after WebSocket upgrade containing the JWT."""

    type: str = InboundType.AUTH
    payload: AuthPayload


class AuthPayload(BaseModel):
    """@brief Payload for the auth message."""

    token: str


class PingMessage(BaseModel):
    """@brief Client heartbeat."""

    type: str = InboundType.PING
    payload: dict[str, Any] = Field(default_factory=dict)


class TypingInMessage(BaseModel):
    """@brief Client indicates they are typing (Phase 2: scoped to channel)."""

    type: str = InboundType.TYPING
    payload: TypingPayload


class TypingPayload(BaseModel):
    """@brief Payload for typing indicators."""

    channel_id: str | None = None


# ── Outbound messages (server → client) ──────────────────────────────────


class AuthOkMessage(BaseMessage):
    """@brief Sent after successful WebSocket authentication."""

    type: str = OutboundType.AUTH_OK
    payload: dict[str, Any] = Field(default_factory=lambda: {"message": "authenticated"})


class AuthErrorMessage(BaseMessage):
    """@brief Sent when WebSocket authentication fails."""

    type: str = OutboundType.AUTH_ERROR


class PongMessage(BaseMessage):
    """@brief Server response to a client ping."""

    type: str = OutboundType.PONG


class NotificationMessage(BaseMessage):
    """
    @brief Server push notification delivered via SSE or WebSocket.

    @param payload Contains ``id``, ``title``, ``body``, ``action_url``, etc.
    """

    type: str = OutboundType.NOTIFICATION


class FeedUpdateMessage(BaseMessage):
    """
    @brief Signals a new post, comment, or reaction in the activity feed.

    @param payload Contains ``event`` (created/updated/deleted) and entity data.
    """

    type: str = OutboundType.FEED_UPDATE


class PresenceMessage(BaseMessage):
    """
    @brief Online presence change broadcast.

    @param payload Contains ``user_id``, ``status`` (online/offline).
    """

    type: str = OutboundType.PRESENCE


class TypingOutMessage(BaseMessage):
    """@brief Broadcast that a user is typing."""

    type: str = OutboundType.TYPING


# ── Helpers ───────────────────────────────────────────────────────────────


def parse_inbound(raw: dict[str, Any]) -> BaseMessage:
    """
    @brief Parse a raw dict from a WebSocket frame into a typed message.

    @param raw Deserialized JSON dict.
    @return A BaseMessage (callers switch on ``.type``).
    """
    return BaseMessage(**raw)


def build_outbound(msg_type: OutboundType, payload: dict[str, Any] | None = None) -> str:
    """
    @brief Serialize an outbound message to a JSON string.

    @param msg_type The outbound message type.
    @param payload Optional payload dict.
    @return JSON string ready for sending.
    """
    msg = BaseMessage(type=msg_type, payload=payload or {})
    return msg.model_dump_json()


def build_sse_event(
    event: str,
    data: dict[str, Any],
    event_id: str | None = None,
) -> str:
    """
    @brief Format data as a Server-Sent Event string.

    @param event SSE event name.
    @param data JSON-serializable payload.
    @param event_id Optional event ID for Last-Event-ID support.
    @return Formatted SSE string ending with double newline.
    """
    import json

    lines = []
    if event_id:
        lines.append(f"id: {event_id}")
    lines.append(f"event: {event}")
    lines.append(f"data: {json.dumps(data)}")
    lines.append("")
    lines.append("")
    return "\n".join(lines)
