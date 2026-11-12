"""
@file notification_tasks.py
@brief Celery tasks for push and email notifications.

Routed to the ``notifications`` queue for high-priority delivery.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

import structlog
from celery import Task

from app.core.config import get_settings
from app.db.session import async_session_factory
from app.models.user import User
from app.repositories.branding_repo import BrandingRepository
from app.repositories.push_repo import PushSubscriptionRepository
from app.repositories.settings_repo import SettingsRepository
from app.services.email.sender import EmailSender
from app.services.email.templates import EmailTemplateRenderer
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
