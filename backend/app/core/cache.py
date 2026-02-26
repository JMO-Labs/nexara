"""
@file cache.py
@brief Thin, fault-tolerant cache helpers backed by Valkey DB 2.

All operations degrade gracefully: on any Valkey connection error,
reads return ``None`` and writes become no-ops. This ensures the
application remains functional even if Valkey is temporarily unavailable.

The cache-aside pattern is used throughout the application:
  1. Check cache first.
  2. On miss, load from Postgres.
  3. Write result back to cache with a short TTL.
"""

from __future__ import annotations

import structlog
from redis.asyncio import Redis

logger = structlog.get_logger(__name__)

DEFAULT_TTL: int = 300
"""@brief Default cache TTL in seconds (5 minutes)."""


async def cache_get(client: Redis, key: str) -> str | None:
    """
    @brief Retrieve a value from the cache.

    Returns ``None`` on cache miss **or** on any connection error,
    allowing the caller to fall through to the database transparently.

    @param client Async Redis client connected to cache DB.
    @param key Cache key to look up.
    @return Cached value as string, or None.
    """
    try:
        return await client.get(key)
    except Exception:
        logger.warning("cache_get_failed", key=key, exc_info=True)
        return None


async def cache_set(
    client: Redis,
    key: str,
    value: str,
    ttl: int = DEFAULT_TTL,
) -> bool:
    """
    @brief Store a value in the cache with a TTL.

    On connection error the write is silently dropped — the next request
    will simply experience a cache miss and repopulate.

    @param client Async Redis client connected to cache DB.
    @param key Cache key.
    @param value Value to store (must be a string; callers serialize JSON).
    @param ttl Time-to-live in seconds.
    @return True if the value was stored, False on failure.
    """
    try:
        await client.setex(key, ttl, value)
        return True
    except Exception:
        logger.warning("cache_set_failed", key=key, exc_info=True)
        return False


async def cache_delete(client: Redis, key: str) -> bool:
    """
    @brief Delete a key from the cache (invalidation).

    On connection error the delete is silently dropped — the key will
    expire naturally via its TTL.

    @param client Async Redis client connected to cache DB.
    @param key Cache key to remove.
    @return True if the key was deleted (or did not exist), False on failure.
    """
    try:
        await client.delete(key)
        return True
    except Exception:
        logger.warning("cache_delete_failed", key=key, exc_info=True)
        return False
