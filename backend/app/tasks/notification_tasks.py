"""
@file notification_tasks.py
@brief Celery tasks for push, email and webhook notifications.

Routed to the ``notifications`` queue for high-priority delivery.
"""

from __future__ import annotations

import asyncio
import random
import uuid
from typing import Any

import apprise
import httpx
import structlog
from celery import Task

from app.core.config import get_settings
from app.db.session import async_session_factory
from app.models.notification import Notification
from app.models.user import User
from app.repositories.apprise_repo import AppriseRepository
from app.repositories.branding_repo import BrandingRepository
from app.repositories.push_repo import PushSubscriptionRepository
from app.repositories.settings_repo import SettingsRepository
from app.repositories.webhook_repo import WebhookRepository
from app.services.email.sender import EmailSender
from app.services.email.templates import EmailTemplateRenderer
from app.services.notifications import registry
from app.services.notifications import types as _notification_types  # noqa: F401
from app.services.notifications.webhook_delivery import deliver_webhook
from app.services.push_service import PushService
from app.tasks.celery_app import celery_app

logger = structlog.get_logger(__name__)


async def _send_email_notification_async(
    user_id: uuid.UUID,
    notification_type: str,
    payload: dict[str, Any],
) -> dict[str, str]:
    """
    @brief Async implementation: fetch user, render template, send email.

    @param user_id Recipient user UUID.
    @param notification_type Type for template (mention, comment, etc.).
    @param payload Context for template (message, link, actor_id).
    @return Dict with status (sent or skipped).
    """
    from sqlalchemy import select

    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            logger.warning("send_email_notification_user_not_found", user_id=str(user_id))
            return {"status": "skipped"}
        to_email = user.email
        branding = await BrandingRepository(session).get(user.community_id)
        sender_name = getattr(branding, "email_sender_name", None) or None

    branding_kwargs: dict[str, Any] = {}
    if branding is not None:
        logo_id = branding.email_logo_media_id or branding.logo_light_media_id
        base_url = get_settings().APP_BASE_URL.rstrip("/")
        branding_kwargs = {
            "community_name": branding.community_name,
            "color_primary": branding.color_primary,
            "logo_url": f"{base_url}/api/v1/media/{logo_id}/file" if logo_id else None,
            "footer_text": branding.email_footer_text,
        }

    renderer = EmailTemplateRenderer()
    html, text = renderer.render(
        "notification.html",
        {
            "notification_type": notification_type,
            "message": payload.get("message", ""),
            "link": payload.get("link", ""),
            "actor_id": payload.get("actor_id"),
        },
        **branding_kwargs,
    )

    sender = EmailSender()
    sent = await sender.send(
        to=to_email,
        subject=payload.get("subject", "New notification"),
        html_body=html,
        text_body=text,
        sender_name=sender_name,
    )
    return {"status": "sent" if sent else "skipped"}


async def _send_push_async(user_id: uuid.UUID, payload: dict[str, Any]) -> dict[str, Any]:
    """
    @brief Look up subscriptions and deliver via PushService.

    @param user_id Recipient user UUID.
    @param payload Dict with title, body, url.
    @return Dict with status and subscription count.
    """
    async with async_session_factory() as session:
        push_repo = PushSubscriptionRepository(session)
        subs = await push_repo.list_for_user(user_id)
        if not subs:
            return {"status": "skipped", "count": 0}
        from sqlalchemy import select

        community_id = await session.scalar(select(User.community_id).where(User.id == user_id))
        if community_id is None:
            return {"status": "skipped", "count": 0}
        service = PushService(
            push_repo,
            SettingsRepository(session),
            community_id,
            settings=get_settings(),
        )
        await service.send_push(
            user_id,
            payload.get("title", ""),
            payload.get("body", ""),
            payload.get("url") or "/",
        )
        await session.commit()
        return {"status": "sent", "count": len(subs)}


@celery_app.task(  # type: ignore[untyped-decorator]
    bind=True,
    name="app.tasks.notification_tasks.send_push_notification",
    max_retries=3,
    queue="notifications",
)
def send_push_notification(self: Task, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """
    @brief Send a Web Push notification to all subscriptions for a user.

    PushService.send_push fans out to every subscription itself, so it is
    called once; the subscription count is looked up for the result.

    @param user_id UUID string of the recipient user.
    @param payload Notification payload dict (``title``, ``body``, ``url``).
    @return Dict with ``status`` (sent, skipped or error) and ``count``.
    """
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        logger.error("send_push_notification_invalid_uuid", user_id=user_id)
        return {"status": "skipped", "count": 0}
    try:
        return asyncio.run(_send_push_async(uid, payload))
    except Exception as exc:
        logger.warning("send_push_notification_failed", user_id=user_id, error=str(exc))
        return {"status": "error", "count": 0}


@celery_app.task(  # type: ignore[untyped-decorator]
    bind=True,
    name="app.tasks.notification_tasks.send_email_notification",
    max_retries=3,
    queue="notifications",
)
def send_email_notification(
    self: Task,
    user_id: str,
    notification_type: str,
    payload: dict[str, Any],
) -> dict[str, str]:
    """
    @brief Build an email from a Jinja2 template and send via SMTP.

    @param user_id UUID string of the recipient user.
    @param notification_type Type key for template (e.g. ``comment``, ``mention``).
    @param payload Context dict (message, link, actor_id, subject).
    @return Dict with ``status`` (sent or skipped).
    """
    logger.info(
        "send_email_notification",
        user_id=user_id,
        notification_type=notification_type,
    )
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        logger.error("send_email_notification_invalid_uuid", user_id=user_id)
        return {"status": "error"}

    try:
        return asyncio.run(_send_email_notification_async(uid, notification_type, payload))
    except Exception as exc:
        logger.exception(
            "send_email_notification_failed",
            user_id=user_id,
            error=str(exc),
        )
        raise self.retry(exc=exc)


WEBHOOK_TIMEOUT_SECONDS = 10.0
"""@brief Per-request timeout for webhook POSTs."""


async def _webhook_deliver_async(
    webhook_id: str, notification_id: str, final_attempt: bool
) -> dict[str, str]:
    """
    @brief Load the subscription + notification and attempt one delivery.

    Commits failure/success bookkeeping even when the attempt raises.

    @param webhook_id Subscription UUID string.
    @param notification_id Notification UUID string.
    @param final_attempt True on the last Celery attempt.
    @return Dict with ``status``.
    """
    async with async_session_factory() as session:
        repo = WebhookRepository(session)
        sub = await repo.get(uuid.UUID(webhook_id))
        notif = await session.get(Notification, uuid.UUID(notification_id))
        if sub is None or notif is None or not sub.enabled:
            logger.info("webhook.skipped", webhook_id=webhook_id, notification_id=notification_id)
            return {"status": "skipped"}
        try:
            category: str | None = registry.get(notif.type).category
        except KeyError:
            category = None
        try:
            async with httpx.AsyncClient(timeout=WEBHOOK_TIMEOUT_SECONDS) as client:
                outcome = await deliver_webhook(
                    repo, sub, notif, category, client, final_attempt=final_attempt
                )
        finally:
            await session.commit()
        return {"status": outcome}


class TransientDeliveryError(Exception):
    """@brief Timeout/5xx-style failure that should be retried."""


async def _apprise_deliver_async(
    repo: AppriseRepository, url_id: uuid.UUID, title: str, body: str
) -> str:
    """
    @brief Decrypt (via repo), notify through Apprise and record the outcome.

    Apprise's ``notify`` returns only a bool, so ``False`` is treated as a
    permanent (4xx-style) failure; raised exceptions (timeouts, connection
    errors) are transient.

    @return ``sent``, ``failed`` or ``skipped``.
    @raises TransientDeliveryError on timeout/connection errors.
    """
    row = await repo.get(url_id)
    if row is None or not row.enabled:
        return "skipped"
    apobj = apprise.Apprise()
    apobj.add(row.apprise_url)
    try:
        ok = await asyncio.to_thread(apobj.notify, body=body, title=title)
    except Exception as exc:
        raise TransientDeliveryError(type(exc).__name__) from exc
    if ok:
        await repo.record_success(url_id)
        return "sent"
    count = await repo.record_failure(url_id)
    logger.warning("notif.channel.failed", channel="apprise", url_id=str(url_id), failures=count)
    return "failed"


async def _apprise_deliver_run(url_id: uuid.UUID, title: str, body: str) -> str:
    async with async_session_factory() as session:
        try:
            out = await _apprise_deliver_async(AppriseRepository(session), url_id, title, body)
        finally:
            await session.commit()
        return out


@celery_app.task(  # type: ignore[untyped-decorator]
    bind=True,
    name="app.tasks.notification_tasks.webhook_deliver",
    autoretry_for=(httpx.HTTPError, httpx.TimeoutException),
    max_retries=5,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    queue="notifications",
)
def webhook_deliver(self: Task, webhook_id: str, notification_id: str) -> dict[str, str]:
    """
    @brief Deliver one notification to one webhook subscription.

    5xx, timeouts and transport errors raise and are auto-retried with
    jittered exponential backoff; 4xx counts a failure without retry.

    @param webhook_id Subscription UUID string.
    @param notification_id Notification UUID string.
    @return Dict with ``status`` (delivered, failed, disabled or skipped).
    """
    try:
        uuid.UUID(webhook_id)
        uuid.UUID(notification_id)
    except ValueError:
        logger.error("webhook_deliver_invalid_uuid", webhook_id=webhook_id)
        return {"status": "skipped"}
    final = self.request.retries >= self.max_retries
    return asyncio.run(_webhook_deliver_async(webhook_id, notification_id, final))


@celery_app.task(  # type: ignore[untyped-decorator]
    bind=True,
    name="app.tasks.notification_tasks.apprise_deliver",
    max_retries=5,
    queue="notifications",
)
def apprise_deliver(
    self: Task, url_id: str, notification_id: str, title: str, body: str
) -> dict[str, str]:
    """
    @brief Deliver one notification to one Apprise URL.

    Transient errors retry with exponential backoff and jitter (max 5).

    @param url_id AppriseURL UUID string.
    @param notification_id Source notification UUID string (for logs).
    @param title Message title.
    @param body Message body.
    @return Dict with ``status``.
    """
    try:
        uid = uuid.UUID(url_id)
    except ValueError:
        logger.error("apprise_deliver_invalid_uuid", url_id=url_id)
        return {"status": "skipped"}
    try:
        return {"status": asyncio.run(_apprise_deliver_run(uid, title, body))}
    except TransientDeliveryError as exc:
        logger.warning(
            "notif.channel.failed",
            channel="apprise",
            notification_id=notification_id,
            error=str(exc),
        )
        raise self.retry(
            exc=exc,
            countdown=random.uniform(0, min(2**self.request.retries * 30, 3600)),  # noqa: S311
        ) from exc
