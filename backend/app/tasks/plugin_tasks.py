"""
@file plugin_tasks.py
@brief Celery task delivering one signed plugin webhook (queue ``plugins``).
"""

from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any
from urllib.parse import urlparse

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


class _RetryableStatusError(Exception):
    """@brief Plugin answered 5xx/408/429."""


def _trusted_host(url: str) -> bool:
    host = get_settings().PLUGIN_HOST_URL
    if not host:
        return False
    a, b = urlparse(url), urlparse(host)
    return (a.scheme, a.netloc) == (b.scheme, b.netloc)


async def _post(url: str, body: bytes, headers: dict[str, str]) -> int:
    # Dev flag or the trusted internal plugin host: plain client (no SSRF pin).
    if get_settings().PLUGINS_ALLOW_INSECURE_URLS or _trusted_host(url):
        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=False, trust_env=False) as c:
            return (await c.post(url, content=body, headers=headers)).status_code
    return await safe_post(url, content=body, headers=headers, timeout=TIMEOUT)


async def _dispatch_async(community_id: str, post_id: str, comment_id: str) -> None:
    from app.db.session import async_session_factory
    from app.models.post import Comment, Post
    from app.models.user import User
    from app.plugins.events import dispatch_plugin_event

    cid = uuid.UUID(community_id)
    async with async_session_factory() as session:
        post = await session.get(Post, uuid.UUID(post_id))
        if post is None or post.community_id != cid or post.deleted_at is not None:
            return
        comment = None
        parent_author: uuid.UUID | None = None
        if comment_id:
            comment = await session.get(Comment, uuid.UUID(comment_id))
            if comment is None or comment.community_id != cid or comment.author_id is None:
                return
            if comment.parent_id:
                parent = await session.get(Comment, comment.parent_id)
                parent_author = parent.author_id if parent else None
        author = await session.get(User, comment.author_id if comment else post.author_id)
        if author is None or author.community_id != cid:
            return
        await dispatch_plugin_event(
            session, cid, post=post, comment=comment, author=author, parent_author_id=parent_author
        )


@celery_app.task(name="app.tasks.plugin_tasks.dispatch_plugin_event_task")
def dispatch_plugin_event_task(community_id: str, post_id: str, comment_id: str = "") -> None:
    """
    @brief Post-commit worker step: re-read content in a fresh session, filter, fan out.
    @param comment_id Empty for a post event.
    """
    asyncio.run(_dispatch_async(community_id, post_id, comment_id))


@celery_app.task(
    name="app.tasks.plugin_tasks.deliver_plugin_event",
    bind=True,
    autoretry_for=(httpx.HTTPError, TimeoutError, _RetryableStatusError),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=MAX_RETRIES,
)
def deliver_plugin_event(
    self: Any, endpoint_url: str, encrypted_secret: str, body: str, delivery_id: str
) -> None:
    """
    @brief POST one signed event; retry with jittered backoff on network errors, 5xx, 408, 429.
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
    if status >= 500 or status in _RETRY_4XX:
        logger.warning("plugin_delivery_retry", delivery_id=delivery_id, status=status)
        raise _RetryableStatusError(str(status))
    if status >= 300:
        logger.warning("plugin_delivery_rejected", delivery_id=delivery_id, status=status)
