"""
@file notification_tasks.py
@brief Celery tasks for push and email notifications.

Routed to the ``notifications`` queue for high-priority delivery.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from celery import Task

from app.core.config import get_settings
from app.db.session import async_session_factory
from app.models.notification import Notification
from app.models.user import User
from app.repositories.branding_repo import BrandingRepository
from app.repositories.digest_repo import DigestRepository
from app.repositories.push_repo import PushSubscriptionRepository
from app.repositories.settings_repo import SettingsRepository
from app.services.email.sender import EmailSender
from app.services.email.templates import EmailTemplateRenderer
from app.services.notifications.digest import should_send_now
from app.services.push_service import PushService
from app.tasks.celery_app import celery_app

logger = structlog.get_logger(__name__)


def _branding_kwargs(branding: Any) -> dict[str, Any]:
    """@brief Map a branding row to EmailTemplateRenderer kwargs ({} when None)."""
    if branding is None:
        return {}
    logo_id = branding.email_logo_media_id or branding.logo_light_media_id
    base_url = get_settings().APP_BASE_URL.rstrip("/")
    return {
        "community_name": branding.community_name,
        "color_primary": branding.color_primary,
        "logo_url": f"{base_url}/api/v1/media/{logo_id}/file" if logo_id else None,
        "footer_text": branding.email_footer_text,
    }


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

    branding_kwargs = _branding_kwargs(branding)

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


async def _digest_dispatch_async(now: datetime) -> int:
    """
    @brief Drain due (user, type) digests and spawn send_digest_email tasks.

    @param now Current aware time.
    @return Number of send_digest_email tasks spawned.
    """
    to_send: list[tuple[str, str, list[str]]] = []
    async with async_session_factory() as session:
        repo = DigestRepository(session)
        settings_repo = SettingsRepository(session)
        for user_id in await repo.list_users_with_pending():
            st = await settings_repo.get_by_user_id(user_id)
            if st is None:
                continue
            cadence = st.digest_cadence or {}
            last = st.digest_last_sent_at
            sent = False
            for type_key in await repo.list_pending_types(user_id):
                mode = cadence.get(type_key, "instant")
                # instant rows are always due; off rows are drained and dropped
                due = mode in ("instant", "off") or should_send_now(
                    mode, last, now, st.dnd_timezone or "UTC"
                )
                if not due:
                    continue
                ids = await repo.drain(user_id, type_key)
                if ids and mode != "off":
                    to_send.append((str(user_id), type_key, [str(i) for i in ids]))
                    sent = True
            if sent:
                st.digest_last_sent_at = now
        await session.commit()
    # Only enqueue emails once the drain is durably committed.
    for uid, type_key, ids in to_send:
        send_digest_email.delay(uid, type_key, ids)
    return len(to_send)


async def _send_digest_email_async(
    user_id: uuid.UUID, type_key: str, notification_ids: list[uuid.UUID]
) -> dict[str, str]:
    """
    @brief Fetch notifications, render the digest template and send it.

    @param user_id Recipient user UUID.
    @param type_key Notification type of the digest.
    @param notification_ids Notifications to include.
    @return Dict with status (sent or skipped).
    """
    from sqlalchemy import select

    async with async_session_factory() as session:
        user = await session.get(User, user_id)
        if user is None:
            logger.warning("send_digest_email_user_not_found", user_id=str(user_id))
            return {"status": "skipped"}
        res = await session.execute(
            select(Notification)
            .where(Notification.id.in_(notification_ids), Notification.user_id == user_id)
            .order_by(Notification.created_at)
        )
        notes = list(res.scalars().all())
        if not notes:
            return {"status": "skipped"}
        to_email = user.email
        branding = await BrandingRepository(session).get(user.community_id)
    items = [
        {"message": n.payload.get("message", ""), "link": n.payload.get("link", "")} for n in notes
    ]
    html, text = EmailTemplateRenderer().render(
        "digest.html",
        {"notification_type": type_key, "items": items},
        **_branding_kwargs(branding),
    )
    label = type_key.replace("_", " ")
    sent = await EmailSender().send(
        to=to_email,
        subject=f"{len(items)} new {label} notification{'' if len(items) == 1 else 's'}",
        html_body=html,
        text_body=text,
        sender_name=getattr(branding, "email_sender_name", None) or None,
    )
    return {"status": "sent" if sent else "skipped"}


@celery_app.task(  # type: ignore[untyped-decorator]
    name="app.tasks.notification_tasks.digest_dispatch",
    queue="notifications",
)
def digest_dispatch() -> int:
    """@brief Beat task (every 5 min): spawn digest emails for due users/types."""
    return asyncio.run(_digest_dispatch_async(datetime.now(UTC)))


@celery_app.task(  # type: ignore[untyped-decorator]
    bind=True,
    name="app.tasks.notification_tasks.send_digest_email",
    max_retries=3,
    queue="notifications",
)
def send_digest_email(
    self: Task, user_id: str, type_key: str, notification_ids: list[str]
) -> dict[str, str]:
    """
    @brief Render and send one digest email.

    @param user_id UUID string of the recipient.
    @param type_key Notification type key.
    @param notification_ids UUID strings of notifications to include.
    @return Dict with ``status`` (sent, skipped or error).
    """
    try:
        uid = uuid.UUID(user_id)
        ids = [uuid.UUID(i) for i in notification_ids]
    except ValueError:
        logger.error("send_digest_email_invalid_uuid", user_id=user_id)
        return {"status": "error"}
    try:
        return asyncio.run(_send_digest_email_async(uid, type_key, ids))
    except Exception as exc:
        logger.exception("send_digest_email_failed", user_id=user_id, error=str(exc))
        raise self.retry(exc=exc)
