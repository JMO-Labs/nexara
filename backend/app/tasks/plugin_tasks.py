"""
@file plugin_tasks.py
@brief Celery task delivering one signed plugin webhook (queue ``plugins``).
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx
import structlog

from app.core.config import get_settings
from app.core.encryption import decrypt_secret, derive_fernet_key
from app.core.http_safe import UnsafeUrlError, safe_post
from app.plugins.signing import sign
from app.tasks.celery_app import celery_app

logger = structlog.get_logger(__name__)

TIMEOUT = 10.0
MAX_RETRIES = 5
_RETRY_4XX = {408, 429}


async def _post(url: str, body: bytes, headers: dict[str, str]) -> int:
    if get_settings().PLUGINS_ALLOW_INSECURE_URLS:
        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=False) as c:
            return (await c.post(url, content=body, headers=headers)).status_code
    return await safe_post(url, content=body, headers=headers, timeout=TIMEOUT)


@celery_app.task(
    name="app.tasks.plugin_tasks.deliver_plugin_event", bind=True, max_retries=MAX_RETRIES
)
def deliver_plugin_event(
    self: Any, endpoint_url: str, encrypted_secret: str, body: str, delivery_id: str
) -> None:
    """
    @brief POST one signed event; retry with backoff on network errors, 5xx, 408, 429.
    @param endpoint_url Plugin events URL.
    @param encrypted_secret Fernet-encrypted webhook secret.
    @param body JSON request body (never logged).
    @param delivery_id Idempotency id sent in ``X-Nexara-Delivery``.
    """
    secret = decrypt_secret(encrypted_secret, derive_fernet_key(get_settings().SECRET_KEY))
    raw = body.encode()
    ts = int(time.time())
    headers = {
        "Content-Type": "application/json",
        "X-Nexara-Delivery": delivery_id,
        "X-Nexara-Timestamp": str(ts),
        "X-Nexara-Signature": sign(secret, ts, raw),
    }
    try:
        status = asyncio.run(_post(endpoint_url, raw, headers))
    except UnsafeUrlError:
        logger.warning("plugin_delivery_blocked", delivery_id=delivery_id)
        return
    except (httpx.HTTPError, TimeoutError) as exc:
        logger.warning("plugin_delivery_error", delivery_id=delivery_id, error=type(exc).__name__)
        raise self.retry(exc=exc, countdown=2**self.request.retries) from exc
    if status >= 500 or status in _RETRY_4XX:
        logger.warning("plugin_delivery_retry", delivery_id=delivery_id, status=status)
        raise self.retry(
            exc=RuntimeError(f"plugin returned {status}"), countdown=2**self.request.retries
        )
    if status >= 400:
        logger.warning("plugin_delivery_rejected", delivery_id=delivery_id, status=status)
