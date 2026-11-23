"""
@file sender.py
@brief The single async SMTP sender (aiosmtplib) used by every email path.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import Any

import structlog
from aiosmtplib import SMTP
from sqlalchemy import update

from app.models.community import Community
from app.services.email.smtp_settings import SmtpConfig

logger = structlog.get_logger(__name__)

_ERR_MAX = 300


async def _record(community_id: uuid.UUID | None, error: str | None) -> None:
    """@brief Best-effort store of smtp_last_ok_at / smtp_last_error for the community row."""
    if community_id is None:
        return
    from app.db.session import async_session_factory

    values: dict[str, Any] = {"smtp_last_ok_at": datetime.now(UTC), "smtp_last_error": None}
    if error is not None:
        values = {"smtp_last_error": error}
    try:
        async with async_session_factory() as session:
            await session.execute(
                update(Community).where(Community.id == community_id).values(**values)
            )
            await session.commit()
    except Exception as exc:  # status is informational; never break a send
        logger.warning("smtp_status_record_failed", error=type(exc).__name__)


def scrub_error(exc: Exception, cfg: SmtpConfig) -> str:
    """@brief Public: error text, truncated, with the password removed."""
    text = f"{type(exc).__name__}: {exc}"
    for secret in (cfg.password, cfg.password.replace(" ", ""), cfg.google_refresh):
        if secret:
            text = text.replace(secret, "***")
    return text[:_ERR_MAX]


async def send_email(
    cfg: SmtpConfig,
    to: str,
    subject: str,
    html: str,
    text: str | None = None,
    *,
    list_unsubscribe: str | None = None,
    sender_name: str | None = None,
    reply_to: str | None = None,
    record: bool = True,
) -> None:
    """
    @brief Send one multipart email over SMTP.
    @param cfg Resolved SMTP config (see resolve_smtp).
    @param to Recipient address.
    @param subject Subject line.
    @param html HTML body.
    @param text Optional plain-text body.
    @param list_unsubscribe Optional List-Unsubscribe header value.
    @param sender_name Display name for From (overrides cfg.from_name).
    @param reply_to Optional Reply-To address.
    @param record Update smtp_last_ok_at / smtp_last_error on the community row.
    @throws Exception whatever the SMTP transport raised (after recording it).
    """
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    name = sender_name or cfg.from_name
    msg["From"] = formataddr((name, cfg.from_addr)) if name else cfg.from_addr
    msg["To"] = to
    if reply_to:
        msg["Reply-To"] = reply_to
    if list_unsubscribe:
        msg["List-Unsubscribe"] = list_unsubscribe
    msg.attach(MIMEText(text or html, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    password = cfg.password
    if cfg.host == "smtp.gmail.com":
        password = password.replace(" ", "")  # app passwords are shown grouped
    try:
        async with SMTP(
            hostname=cfg.host,
            port=cfg.port,
            username=cfg.user or None,
            password=password or None,
            use_tls=cfg.security == "ssl",
            start_tls=cfg.security == "starttls",
        ) as smtp:
            await smtp.send_message(msg)
    except Exception as exc:
        logger.error("email_send_failed", to=to, subject=subject, error=type(exc).__name__)
        if record:
            await _record(cfg.community_id, scrub_error(exc, cfg))
        raise
    logger.info("email_sent", to=to, subject=subject)
    if record:
        await _record(cfg.community_id, None)
