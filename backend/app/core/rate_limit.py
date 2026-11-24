"""
@file rate_limit.py
@brief Rate limiting configuration via slowapi.

Uses a Redis (Valkey) backend for sliding-window rate limiting.
Falls back to in-memory storage when Redis is unavailable.

The ``limiter`` instance is attached to ``app.state.limiter`` in ``main.py``
and activated by the ``SlowAPIMiddleware``.
"""

from __future__ import annotations

import structlog
from fastapi import Request
from slowapi import Limiter

from app.core.client_ip import client_ip
from app.core.config import get_settings

logger = structlog.get_logger(__name__)


def _build_storage_uri() -> str | None:
    """
    @brief Build the Redis storage URI for slowapi.

    Returns the Valkey cache URL (DB 2) for production use.
    Returns None to use in-memory storage as fallback.
    """
    try:
        settings = get_settings()
        return settings.redis_cache_url
    except Exception:
        logger.warning("rate_limit_redis_unavailable_using_memory", exc_info=True)
        return None


def rate_limit_key(request: Request) -> str:
    """
    @brief Bucket key = real client IP behind our proxy (not nginx's 127.0.0.1).

    @param request Current request.
    @return Client IP, or ``"unknown"`` when none can be determined.
    """
    return client_ip(request) or "unknown"


storage_uri = _build_storage_uri()

limiter = Limiter(
    key_func=rate_limit_key,
    default_limits=[get_settings().RATE_LIMIT_DEFAULT],
    storage_uri=storage_uri or "memory://",
    strategy="fixed-window",
)
"""@brief Global rate limiter instance attached to the app in ``main.py``."""
