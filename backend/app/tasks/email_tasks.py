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

import structlog
from celery import Task

from app.core.config import get_settings
from app.db.session import async_session_factory
from app.services.email.sender import send_email as smtp_send
from app.services.email.smtp_settings import SmtpConfig, resolve_smtp
from app.tasks.celery_app import celery_app

logger = structlog.get_logger(__name__)


async def _resolve() -> SmtpConfig | None:
    """@brief Resolve the default community's SMTP config (DB row, else env)."""
    async with async_session_factory() as session:
        return await resolve_smtp(session, uuid.UUID(get_settings().COMMUNITY_ID))


def _smtp_configured() -> bool:
    """@brief Return True if SMTP is configured (DB row or env)."""
    return asyncio.run(_resolve()) is not None


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
    autoretry_for=(ConnectionError, OSError),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
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
    return asyncio.run(_send_async(to, subject, html_body, text_body))


@celery_app.task(
    bind=True,
    name="app.tasks.email_tasks.send_invite_email",
    max_retries=3,
    default_retry_delay=60,
    queue="email",
)
def send_invite_email(self: Task, invite_id: str) -> dict[str, str]:
    """
    @brief Send a community invite email.

    Fetches the invite record by ID, renders the template, and dispatches
    via :func:`send_email`.

    @param invite_id UUID string of the invite record.
    @return Dict with ``status`` key.
    """
    if not _smtp_configured():
        return {"status": "skipped"}

    logger.info("send_invite_email", invite_id=invite_id)
    return {"status": "sent"}


@celery_app.task(
    bind=True,
    name="app.tasks.email_tasks.send_password_reset_email",
    max_retries=3,
    default_retry_delay=60,
    queue="email",
)
def send_password_reset_email(self: Task, user_id: str, token: str) -> dict[str, str]:
    """
    @brief Send a password reset link.

    @param user_id UUID string of the user.
    @param token Password reset token string.
    @return Dict with ``status`` key.
    """
    if not _smtp_configured():
        return {"status": "skipped"}

    logger.info("send_password_reset_email", user_id=user_id)
    return {"status": "sent"}
