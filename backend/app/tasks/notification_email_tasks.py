"""
@file notification_email_tasks.py
@brief Celery tasks that email a notification or digest.

Task names keep the legacy ``app.tasks.notification_tasks.*`` dotted path so
queued messages and the beat schedule keep resolving.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

import structlog
from celery import Task

from app.core.config import get_settings
from app.db.session import async_session_factory
from app.models.notification import Notification
from app.models.user import User
from app.repositories.branding_repo import BrandingRepository
from app.services.email.sender import SmtpSendError, send_email
from app.services.email.smtp_settings import resolve_smtp
from app.services.email.templates import EmailTemplateRenderer
from app.tasks.celery_app import celery_app

logger = structlog.get_logger(__name__)

_RETRYABLE = frozenset({"connect_failed", "timeout"})


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


REPLY_TYPES = frozenset({"comment", "mention", "new_post"})
"""@brief Notification types whose email may carry a reply-by-email address."""


async def _reply_to(
    session: Any, user: User, notification_type: str, payload: dict[str, Any]
) -> str | None:
    """
    @brief Mint a fresh reply token and return the Reply-To address.

    None unless the type is replyable, the post is known, and the feature is
    on with complete settings. Never raises: the email goes out regardless.
    """
    from app.repositories.community_repo import CommunityRepository
    from app.repositories.reply_token_repo import ReplyTokenRepository
    from app.services.email import reply_address

    if notification_type not in REPLY_TYPES or not payload.get("post_id"):
        return None
    try:
        community = await CommunityRepository(session).get(user.community_id)
        if community is None or not reply_address.is_active(community):
            return None
        token = await ReplyTokenRepository(session).create(
            user.community_id, user.id, uuid.UUID(str(payload["post_id"]))
        )
        await session.commit()
        return reply_address.with_token(community.inbound_reply_address or "", token)
    except Exception as exc:
        logger.warning("reply_to_unavailable", error=type(exc).__name__)
        return None


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
        reply_to = await _reply_to(session, user, notification_type, payload)
        cfg = await resolve_smtp(session, user.community_id)
    if cfg is None:
        logger.debug("email_skipped_smtp_not_configured", user_id=str(user_id))
        return {"status": "skipped"}

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

    await send_email(
        cfg,
        to_email,
        payload.get("subject", "New notification"),
        html,
        text,
        sender_name=sender_name,
        reply_to=reply_to,
    )
    return {"status": "sent"}


@celery_app.task(
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
    except SmtpSendError as exc:
        logger.warning("send_email_notification_failed", user_id=user_id, category=exc.category)
        if exc.category in _RETRYABLE:  # transient; auth/rejection won't fix themselves
            raise self.retry(exc=exc) from exc
        raise


def digest_notes_stmt(user_id: uuid.UUID, notification_ids: list[uuid.UUID]) -> Any:
    """
    @brief The recipient's digest notifications, minus any whose post, album or
           photo is NSFW (possibly flagged after storing) for a non-adult.
    """
    from sqlalchemy import select

    from app.repositories.visibility_preds import payload_nsfw_ok

    return (
        select(Notification)
        .where(
            Notification.id.in_(notification_ids),
            Notification.user_id == user_id,
            payload_nsfw_ok(Notification.payload, user_id),
        )
        .order_by(Notification.created_at)
    )


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
    async with async_session_factory() as session:
        user = await session.get(User, user_id)
        if user is None:
            logger.warning("send_digest_email_user_not_found", user_id=str(user_id))
            return {"status": "skipped"}
        res = await session.execute(digest_notes_stmt(user_id, notification_ids))
        notes = list(res.scalars().all())
        if not notes:
            return {"status": "skipped"}
        to_email = user.email
        branding = await BrandingRepository(session).get(user.community_id)
        cfg = await resolve_smtp(session, user.community_id)
    if cfg is None:
        return {"status": "skipped"}
    items = [
        {"message": n.payload.get("message", ""), "link": n.payload.get("link", "")} for n in notes
    ]
    html, text = EmailTemplateRenderer().render(
        "digest.html",
        {"notification_type": type_key, "items": items},
        **_branding_kwargs(branding),
    )
    label = type_key.replace("_", " ")
    await send_email(
        cfg,
        to_email,
        f"{len(items)} new {label} notification{'' if len(items) == 1 else 's'}",
        html,
        text,
        sender_name=getattr(branding, "email_sender_name", None) or None,
    )
    return {"status": "sent"}


@celery_app.task(
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
    except SmtpSendError as exc:
        logger.warning("send_digest_email_failed", user_id=user_id, category=exc.category)
        if exc.category in _RETRYABLE:
            raise self.retry(exc=exc) from exc
        raise
