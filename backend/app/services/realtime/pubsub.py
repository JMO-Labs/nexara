"""
@file pubsub.py
@brief Valkey pub/sub publisher and subscriber for cross-instance realtime delivery.

When multiple API instances run behind a load balancer, a message published
by instance A reaches users connected to instance B via Valkey pub/sub.

Channels:
  - ``user:{user_id}``        — messages targeted at a specific user
  - ``community:{community_id}`` — broadcast to all users in a community
  - ``presence``               — online/offline status changes
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from uuid import UUID

import structlog

from app.core.config import get_settings
from app.core.valkey import DB_PUBSUB, get_pool
from app.services.realtime.connection_manager import manager

logger = structlog.get_logger(__name__)

_subscriber_task: asyncio.Task[None] | None = None


async def publish(channel: str, message: dict[str, Any]) -> int:
    """
    @brief Publish a message to a Valkey pub/sub channel.

    @param channel Channel name (e.g. ``user:abc-123``).
    @param message JSON-serializable payload.
    @return Number of subscribers that received the message.
    """
    settings = get_settings()
    pool = get_pool(settings, DB_PUBSUB)
    data = json.dumps(message)
    result = await pool.publish(channel, data)
    logger.debug("pubsub_published", channel=channel, receivers=result)
    return int(result)


async def publish_to_user(user_id: UUID, message: dict[str, Any]) -> int:
    """
    @brief Convenience wrapper: publish to the user-specific channel.

    @param user_id Target user UUID.
    @param message Message payload.
    @return Number of pub/sub subscribers reached.
    """
    return await publish(f"user:{user_id}", message)


async def publish_to_community(community_id: UUID, message: dict[str, Any]) -> int:
    """
    @brief Publish to the community broadcast channel.

    @param community_id Community UUID.
    @param message Message payload.
    @return Number of pub/sub subscribers reached.
    """
    return await publish(f"community:{community_id}", message)


async def _handle_message(channel: str, data: str) -> None:
    """
    @brief Dispatch a received pub/sub message to local connections.

    @param channel The channel the message was published on.
    @param data Raw JSON string.
    """
    try:
        message = json.loads(data)
    except json.JSONDecodeError:
        logger.warning("pubsub_invalid_json", channel=channel)
        return

    if channel.startswith("user:"):
        user_id_str = channel.split(":", 1)[1]
        try:
            uid = UUID(user_id_str)
        except ValueError:
            return
        await manager.send_to_user(uid, message)

    elif channel.startswith("community:"):
        community_id_str = channel.split(":", 1)[1]
        try:
            cid = UUID(community_id_str)
        except ValueError:
            return
        await manager.send_to_community(cid, message)

    elif channel == "presence":
        await manager.broadcast(message)


async def start_subscriber() -> None:
    """
    @brief Start the background Valkey pub/sub listener.

    Subscribes to user-specific, community, and presence channels.
    Dispatches received messages to the local :data:`manager`.
    """
    global _subscriber_task

    if _subscriber_task and not _subscriber_task.done():
        return

    _subscriber_task = asyncio.create_task(_subscriber_loop())
    logger.info("pubsub_subscriber_started")


async def _subscriber_loop() -> None:
    """@brief Long-running loop that reads from Valkey pub/sub."""
    settings = get_settings()
    pool = get_pool(settings, DB_PUBSUB)

    pubsub = pool.pubsub()
    await pubsub.psubscribe("user:*", "community:*", "presence")

    try:
        while True:
            msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if msg and msg["type"] in ("pmessage", "message"):
                channel = msg.get("channel", b"")
                if isinstance(channel, bytes):
                    channel = channel.decode()
                data = msg.get("data", b"")
                if isinstance(data, bytes):
                    data = data.decode()
                await _handle_message(channel, data)
            else:
                await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        logger.info("pubsub_subscriber_cancelled")
    except Exception:
        logger.exception("pubsub_subscriber_error")
    finally:
        await pubsub.punsubscribe()
        await pubsub.close()


async def stop_subscriber() -> None:
    """@brief Cancel the background subscriber task gracefully."""
    global _subscriber_task
    if _subscriber_task and not _subscriber_task.done():
        _subscriber_task.cancel()
        try:
            await _subscriber_task
        except asyncio.CancelledError:
            pass
    _subscriber_task = None
    logger.info("pubsub_subscriber_stopped")
