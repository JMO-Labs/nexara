"""
@file presence.py
@brief Online presence tracking via Valkey sorted set.

Users are tracked in a sorted set ``presence:online`` with:
  - member = user_id (string)
  - score  = Unix timestamp of last heartbeat

Users who haven't sent a heartbeat within 5 minutes are considered offline.
A periodic Celery task calls :func:`cleanup_stale` to prune old entries.
"""

from __future__ import annotations

import time
from uuid import UUID

import structlog

from app.core.config import get_settings
from app.core.metrics import users_online
from app.core.valkey import DB_PUBSUB, get_pool

logger = structlog.get_logger(__name__)

PRESENCE_KEY = "presence:online"
"""@brief Valkey sorted set key for online presence."""

PRESENCE_TTL_SECONDS = 300
"""@brief Users inactive for longer than this are considered offline (5 minutes)."""


async def set_online(user_id: UUID) -> None:
    """
    @brief Mark a user as online (or refresh their heartbeat).

    @param user_id UUID of the user.
    """
    settings = get_settings()
    pool = get_pool(settings, DB_PUBSUB)
    await pool.zadd(PRESENCE_KEY, {str(user_id): time.time()})
    logger.debug("presence_online", user_id=str(user_id))


async def set_offline(user_id: UUID) -> None:
    """
    @brief Mark a user as offline.

    @param user_id UUID of the user.
    """
    settings = get_settings()
    pool = get_pool(settings, DB_PUBSUB)
    await pool.zrem(PRESENCE_KEY, str(user_id))
    logger.debug("presence_offline", user_id=str(user_id))


async def get_online_users() -> list[str]:
    """
    @brief Return user IDs that have been active within the TTL window.

    @return List of user ID strings.
    """
    settings = get_settings()
    pool = get_pool(settings, DB_PUBSUB)
    cutoff = time.time() - PRESENCE_TTL_SECONDS
    members = await pool.zrangebyscore(PRESENCE_KEY, cutoff, "+inf")
    return [m.decode() if isinstance(m, bytes) else m for m in members]


async def get_online_count() -> int:
    """
    @brief Return the number of currently online users.

    @return Integer count of online users.
    """
    settings = get_settings()
    pool = get_pool(settings, DB_PUBSUB)
    cutoff = time.time() - PRESENCE_TTL_SECONDS
    return await pool.zcount(PRESENCE_KEY, cutoff, "+inf")


async def is_online(user_id: UUID) -> bool:
    """
    @brief Check if a specific user is currently online.

    @param user_id UUID of the user.
    @return True if the user has a recent heartbeat.
    """
    settings = get_settings()
    pool = get_pool(settings, DB_PUBSUB)
    score = await pool.zscore(PRESENCE_KEY, str(user_id))
    if score is None:
        return False
    return (time.time() - score) < PRESENCE_TTL_SECONDS


async def cleanup_stale() -> int:
    """
    @brief Remove entries older than the TTL window.

    Intended to be called by a periodic Celery task (e.g. every 60 seconds).

    @return Number of stale entries removed.
    """
    settings = get_settings()
    pool = get_pool(settings, DB_PUBSUB)
    cutoff = time.time() - PRESENCE_TTL_SECONDS
    removed = await pool.zremrangebyscore(PRESENCE_KEY, "-inf", cutoff)

    count = await get_online_count()
    users_online.set(count)

    logger.debug("presence_cleanup", removed=removed, online=count)
    return removed
