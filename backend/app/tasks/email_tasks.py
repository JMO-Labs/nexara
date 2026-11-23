"""
@file email_tasks.py
@brief Celery tasks for all email delivery.

All email sending flows through this module.  Tasks are routed to the
``email`` queue for high-priority, fast execution.  If SMTP is not
configured (no DB settings and no ``SMTP_HOST``), tasks become no-ops.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Coroutine
from dataclasses import dataclass
from typing import Any

import structlog
from celery import Task

from app.core.config import get_settings
from app.db.session import async_session_factory
from app.models.invite import Invite
from app.models.user import User
from app.repositories.branding_repo import BrandingRepository
from app.services.email.sender import SmtpSendError
from app.services.email.sender import send_email as smtp_send
from app.services.email.smtp_settings import SmtpConfig, resolve_smtp
from app.services.email.templates import EmailTemplateRenderer
from app.tasks.celery_app import celery_app
from app.tasks.notification_tasks import _branding_kwargs

logger = structlog.get_logger(__name__)

_RETRYABLE = frozenset({"connect_failed", "timeout"})


async def _resolve() -> SmtpConfig | None:
    """@brief Resolve the default community's SMTP config (DB row, else env)."""
    async with async_session_factory() as session:
        return await resolve_smtp(session, uuid.UUID(get_settings().COMMUNITY_ID))


async def _send_async(
    to: str, subject: str, html_body: str, text_body: str | None
) -> dict[str, str]:
    """@brief Resolve config and send through the single sender."""
    cfg = await _resolve()
    if cfg is None:
        logger.info("email_skipped_smtp_not_configured", to=to, subject=subject)
        return {"status": "skipped"}
    await smtp_send(cfg, to, subject, html_body, text_body)
    return {"status": "sent"}


@celery_app.task(
    bind=True,
    name="app.tasks.email_tasks.send_email",
    max_retries=3,
    default_retry_delay=30,
    queue="email",
)
def send_email(
    self: Task,
    to: str,
    subject: str,
    html_body: str,
    text_body: str | None = None,
) -> dict[str, str]:
    """
    @brief Send a single email via SMTP.

    No-ops gracefully if SMTP is not configured.  All higher-level email
    tasks (invite, password reset, notification) call this task.

    @param to Recipient email address.
    @param subject Email subject line.
    @param html_body HTML body content.
    @param text_body Optional plain-text fallback body.
    @return Dict with ``status`` key (``"sent"`` or ``"skipped"``).
    """
    try:
        return asyncio.run(_send_async(to, subject, html_body, text_body))
    except SmtpSendError as exc:
        if exc.category in _RETRYABLE:  # transient; auth/rejection won't fix themselves
            raise self.retry(exc=exc) from exc
        raise


@dataclass
class _MailCtx:
    """@brief Everything an invite/reset mail needs, loaded in one DB session."""

    cfg: SmtpConfig | None
    to: str
    inviter: str
    branding: dict[str, Any]
    sender_name: str | None


async def _branding_ctx(session: Any, community_id: uuid.UUID) -> tuple[dict[str, Any], str | None]:
    branding = await BrandingRepository(session).get(community_id)
    return _branding_kwargs(branding), getattr(branding, "email_sender_name", None) or None


async def _invite_ctx(invite_id: str) -> _MailCtx | None:
    """@brief Load an unused invite's mail context; None when gone or already used."""
    async with async_session_factory() as session:
        invite = await session.get(Invite, uuid.UUID(invite_id))
        if invite is None or invite.used_at is not None:
            logger.info("invite_email.invite_not_found", invite_id=invite_id)
            return None
        creator = await session.get(User, invite.created_by)
        branding, sender = await _branding_ctx(session, invite.community_id)
        cfg = await resolve_smtp(session, invite.community_id)
        return _MailCtx(
            cfg, invite.email, creator.display_name if creator else "", branding, sender
        )


async def _reset_ctx(user_id: str) -> _MailCtx | None:
    """@brief Load an active user's mail context; None when gone or disabled."""
    async with async_session_factory() as session:
        user = await session.get(User, uuid.UUID(user_id))
        if user is None or user.deleted_at is not None or not user.is_active:
            return None
        branding, sender = await _branding_ctx(session, user.community_id)
        cfg = await resolve_smtp(session, user.community_id)
        return _MailCtx(cfg, user.email, "", branding, sender)


async def _deliver(
    ctx: _MailCtx | None, template: str, params: dict[str, Any], subject: str, kind: str
) -> dict[str, str]:
    """@brief Render and send one mail through the single sender; skip when unconfigured."""
    if ctx is None:
        return {"status": "skipped"}
    if ctx.cfg is None:
        logger.info("email.not_configured", kind=kind)
        return {"status": "skipped"}
    html, text = EmailTemplateRenderer().render(template, params, **ctx.branding)
    await smtp_send(ctx.cfg, ctx.to, subject, html, text)
    return {"status": "sent"}


def _base() -> str:
    return get_settings().APP_BASE_URL.rstrip("/")


def _run(task: Task, coro: Coroutine[Any, Any, dict[str, str]]) -> dict[str, str]:
    """@brief Run a delivery; transient SMTP failures retry, the rest fail the task."""
    try:
        return asyncio.run(coro)
    except SmtpSendError as exc:
        if exc.category in _RETRYABLE:
            raise task.retry(exc=exc) from exc
        raise


@celery_app.task(
    bind=True,
    name="app.tasks.email_tasks.send_invite_email",
    max_retries=3,
    default_retry_delay=60,
    queue="email",
)
def send_invite_email(self: Task, invite_id: str, token: str) -> dict[str, str]:
    """
    @brief Send a community invite email with the registration link.

    @param invite_id UUID string of the invite record.
    @param token Raw invite token (only the hash is stored, so the caller passes it).
    @return Dict with ``status`` key (``sent`` or ``skipped``).
    """

    async def go() -> dict[str, str]:
        ctx = await _invite_ctx(invite_id)
        who = (ctx.inviter if ctx else "") or "Someone"
        name = ctx.branding.get("community_name", "Nexara") if ctx else "Nexara"
        return await _deliver(
            ctx,
            "invite.html",
            {"inviter": who, "invite_url": f"{_base()}/register?invite={token}"},
            f"{who} invited you to {name}",
            "invite",
        )

    return _run(self, go())


@celery_app.task(
    bind=True,
    name="app.tasks.email_tasks.send_password_reset_email",
    max_retries=3,
    default_retry_delay=60,
    queue="email",
)
def send_password_reset_email(self: Task, user_id: str, token: str) -> dict[str, str]:
    """
    @brief Send a password reset link (valid 60 minutes).

    @param user_id UUID string of the user.
    @param token Raw password reset token.
    @return Dict with ``status`` key (``sent`` or ``skipped``).
    """

    async def go() -> dict[str, str]:
        ctx = await _reset_ctx(user_id)
        name = ctx.branding.get("community_name", "Nexara") if ctx else "Nexara"
        return await _deliver(
            ctx,
            "password_reset.html",
            {"reset_url": f"{_base()}/reset-password?token={token}", "expiry_minutes": 60},
            f"Reset your {name} password",
            "password_reset",
        )

    return _run(self, go())
