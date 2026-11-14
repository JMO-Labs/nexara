"""
@file valkey.py
@brief Valkey (Redis-compatible) connection helper module.

Provides connection pool creation and lifecycle management for three logical
databases inside a single Valkey instance:

  - DB 0: Celery task broker (noeviction — tasks must not be lost)
  - DB 1: Pub/Sub for real-time message delivery
  - DB 2: Application cache (allkeys-lru — rebuildable from Postgres)

All pools use the hiredis parser for parsing performance and share
configuration from the application :class:`Settings`.
"""

from __future__ import annotations

import structlog
from redis.asyncio import Redis

from app.core.config import Settings

logger = structlog.get_logger(__name__)

DB_BROKER: int = 0
"""@brief Logical DB index for Celery task broker."""

DB_PUBSUB: int = 1
"""@brief Logical DB index for real-time pub/sub."""

DB_CACHE: int = 2
"""@brief Logical DB index for application cache."""

_pools: dict[int, Redis] = {}
"""@brief Registry of active connection pools, keyed by DB index."""


def get_valkey_url(settings: Settings, db: int) -> str:
    """
    @brief Build a Valkey connection URL for the given logical database.

    @param settings Application settings containing REDIS_URL.
    @param db Logical database index (0, 1, or 2).
    @return Full connection URL with DB suffix, e.g. ``redis://valkey:6379/0``.
    """
    base = settings.REDIS_URL.rstrip("/")
    return f"{base}/{db}"


def create_pool(
    settings: Settings,
    db: int,
    max_connections: int = 10,
    decode_responses: bool = True,
    socket_connect_timeout: float = 5.0,
    socket_timeout: float = 5.0,
) -> Redis:
    """
    @brief Create an async Redis connection pool for the given logical DB.

    Connections are lazily established on first use; this function
    performs no I/O. The created pool is **not** automatically registered
    in the global pool registry — use :func:`get_pool` for managed access.

    @param settings Application settings.
    @param db Logical database index.
    @param max_connections Maximum pool size.
    @param decode_responses If True, decode bytes to str automatically.
    @param socket_connect_timeout Seconds before connect timeout.
    @param socket_timeout Seconds before socket read/write timeout.
    @return Configured :class:`redis.asyncio.Redis` client instance.
    """
    url = get_valkey_url(settings, db)
    return Redis.from_url(  # type: ignore[no-any-return] # third-party stub returns Any
        url,
        max_connections=max_connections,
        decode_responses=decode_responses,
        socket_connect_timeout=socket_connect_timeout,
        socket_timeout=socket_timeout,
    )


def get_pool(settings: Settings, db: int) -> Redis:
    """
    @brief Return the shared pool for a logical DB, creating it if needed.

    Uses a module-level registry so callers share connections for the
    same DB index across the application.

    @param settings Application settings.
    @param db Logical database index.
    @return Shared :class:`redis.asyncio.Redis` client for the given DB.
    """
    if db not in _pools:
        _pools[db] = create_pool(settings, db)
        logger.info("valkey_pool_created", db=db)
    return _pools[db]


async def close_pools() -> None:
    """
    @brief Close all registered connection pools.

    Should be called during application shutdown (e.g. FastAPI lifespan)
    to release all Valkey connections cleanly.
    """
    for db, pool in _pools.items():
        try:
            await pool.aclose()
            logger.info("valkey_pool_closed", db=db)
        except Exception:
            logger.warning("valkey_pool_close_failed", db=db, exc_info=True)
    _pools.clear()


async def check_valkey_health(client: Redis) -> bool:
    """
    @brief Check if Valkey is reachable via PING.

    Used by the ``/healthz`` endpoint to report Valkey status.
    Returns False on any connection error or timeout rather than raising.

    @param client An async Redis client instance.
    @return True if PING succeeds, False otherwise.
    """
    try:
        return bool(await client.ping())
    except Exception:
        logger.warning("valkey_health_check_failed", exc_info=True)
        return False
