"""@file webhook_delivery.py
@brief Webhook payload construction, Stripe-style HMAC signing and a single
delivery attempt with failure bookkeeping.

Retries are owned by the Celery task: this module raises ``httpx`` errors for
retryable outcomes (5xx, timeouts, transport errors) and records permanent
(4xx) failures itself.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any, Literal

import httpx
import structlog

from app.core.config import get_settings
from app.models.notification import Notification
from app.models.webhook import WebhookSubscription
from app.repositories.webhook_repo import WebhookRepository
from app.services.notifications.webhook_guard import is_blocked_destination

logger = structlog.get_logger(__name__)

SIGNATURE_HEADER = "X-Nexara-Signature"
"""@brief Header carrying ``t=<unix_ts>,v1=<hex hmac>``."""

DeliveryOutcome = Literal["delivered", "failed", "disabled"]


def build_payload(notification: Notification, category: str | None) -> dict[str, Any]:
    """
    @brief Build the JSON-serialisable webhook body for a notification.
    @param notification Source notification.
    @param category Registry category of the type (None if unregistered).
    @return Payload dict.
    """
    return {
        "id": str(notification.id),
        "type": notification.type,
        "category": category,
        "user_id": str(notification.user_id),
        "community_id": str(notification.community_id),
        "payload": notification.payload,
        "actor_ids": [str(a) for a in notification.actor_ids],
        "count": notification.count,
        "created_at": notification.created_at.isoformat(),
        "updated_at": notification.updated_at.isoformat(),
    }


def sign(body: str, secret: str, timestamp: int) -> str:
    """
    @brief Stripe-style signature over ``"<timestamp>.<body>"``.
    @param body Exact JSON body sent on the wire.
    @param secret Subscription secret.
    @param timestamp Unix seconds.
    @return ``t=<timestamp>,v1=<hex hmac-sha256>``.
    """
    mac = hmac.new(secret.encode(), f"{timestamp}.{body}".encode(), hashlib.sha256)
    return f"t={timestamp},v1={mac.hexdigest()}"


async def deliver_webhook(
    repo: WebhookRepository,
    sub: WebhookSubscription,
    notification: Notification,
    category: str | None,
    client: httpx.AsyncClient,
    *,
    final_attempt: bool,
) -> DeliveryOutcome:
    """
    @brief POST one signed notification to a subscription.
    @param repo Webhook repository for success/failure bookkeeping.
    @param sub Target subscription.
    @param notification Notification to deliver.
    @param category Registry category for the payload.
    @param client HTTP client (no redirects followed).
    @param final_attempt True when Celery will not retry again; a retryable
        error then counts as a failure before being re-raised.
    @return ``delivered``, ``failed`` (4xx or blocked non-public destination)
        or ``disabled`` (failure threshold hit).
    @raises httpx.HTTPError on 5xx, timeouts or transport errors (retryable).
    """
    body = json.dumps(build_payload(notification, category), separators=(",", ":"))
    headers = {
        "Content-Type": "application/json",
        SIGNATURE_HEADER: sign(body, sub.secret, int(time.time())),
    }
    log = logger.bind(webhook_id=str(sub.id), notification_id=str(notification.id))
    try:
        if await is_blocked_destination(sub.url, get_settings().webhook_allowed_hosts):
            log.warning("notif.channel.failed", channel="webhook", reason="blocked_destination")
            return await _record_failure(repo, sub, log)
        resp = await client.post(sub.url, content=body, headers=headers)
        if resp.status_code >= 500:
            raise httpx.HTTPStatusError(
                f"webhook returned {resp.status_code}", request=resp.request, response=resp
            )
    except httpx.HTTPError as exc:
        log.warning("notif.channel.failed", channel="webhook", error=str(exc), final=final_attempt)
        if final_attempt:
            await _record_failure(repo, sub, log)
        raise
    if resp.is_success:
        await repo.record_success(sub.id)
        log.info("webhook.delivered", status=resp.status_code)
        return "delivered"
    log.warning("notif.channel.failed", channel="webhook", status=resp.status_code)
    return await _record_failure(repo, sub, log)


async def _record_failure(
    repo: WebhookRepository, sub: WebhookSubscription, log: Any
) -> DeliveryOutcome:
    """@brief Count a failure; log ``webhook.disabled`` if it tripped the limit."""
    await repo.record_failure(sub.id)
    if not sub.enabled:
        log.warning("webhook.disabled", failure_count=sub.failure_count)
        return "disabled"
    return "failed"
