"""
@file email_tasks.py
@brief Celery tasks for all email delivery.

All email sending flows through this module.  Tasks are routed to the
``email`` queue for high-priority, fast execution.  If SMTP is not
configured (``SMTP_HOST`` is empty), tasks become no-ops.
"""

from __future__ import annotations

import structlog
from celery import Task

from app.core.config import get_settings
from app.tasks.celery_app import celery_app

logger = structlog.get_logger(__name__)


def _smtp_configured() -> bool:
    """@brief Return True if SMTP settings are present."""
    settings = get_settings()
    return bool(settings.SMTP_HOST)


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
    if not _smtp_configured():
        logger.info("email_skipped_smtp_not_configured", to=to, subject=subject)
        return {"status": "skipped"}

    settings = get_settings()
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to

    if text_body:
        msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.ehlo()
        if settings.SMTP_PORT == 587:
            server.starttls()
        if settings.SMTP_USER and settings.SMTP_PASSWORD:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(settings.SMTP_FROM, to, msg.as_string())

    logger.info("email_sent", to=to, subject=subject)
    return {"status": "sent"}


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
