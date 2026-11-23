"""
@file sender.py
@brief The single async SMTP sender (aiosmtplib) used by every email path.
"""

from __future__ import annotations

import ssl
import uuid
from datetime import UTC, datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import Any

import structlog
from aiosmtplib import SMTP, errors
from sqlalchemy import select, update

from app.models.community import Community
from app.services.email.smtp_settings import SmtpConfig

logger = structlog.get_logger(__name__)

_RECORD_REFRESH = timedelta(minutes=10)

#: category -> human message (the only error text exposed to admins or stored).
MESSAGES = {
    "auth_failed": "The mail server rejected the user name or password.",
    "connect_failed": "Could not connect to the mail server.",
    "tls_failed": "Could not set up an encrypted connection.",
    "rejected": "The mail server rejected the message or an address.",
    "timeout": "The mail server did not answer in time.",
    "unknown": "Sending failed. Check the server log for details.",
}


class SmtpSendError(Exception):
    """@brief Sanitised send failure: a category and a fixed human message, no raw text."""

    def __init__(self, category: str, message: str | None = None) -> None:
        self.category = category
        self.message = message or MESSAGES[category]
        super().__init__(f"{category}: {self.message}")

    @property
    def stored(self) -> str:
        """@brief ``category: message`` as stored in smtp_last_error."""
        return f"{self.category}: {self.message}"


def classify(exc: Exception) -> SmtpSendError:
    """@brief Map an aiosmtplib/socket/ssl exception to a generic SmtpSendError."""
    if isinstance(exc, SmtpSendError):
        return exc
    if isinstance(exc, errors.SMTPAuthenticationError):
        return SmtpSendError("auth_failed")
    if isinstance(exc, ssl.SSLError | errors.SMTPNotSupported):
        return SmtpSendError("tls_failed")
    if isinstance(exc, errors.SMTPTimeoutError | TimeoutError):  # incl. connect timeout
        return SmtpSendError("timeout")
    if isinstance(exc, errors.SMTPConnectError | errors.SMTPServerDisconnected):
        return SmtpSendError("connect_failed")
    if isinstance(exc, errors.SMTPRecipientsRefused | errors.SMTPResponseException):
        return SmtpSendError("rejected")  # sender/recipient/data/helo refusals
    if isinstance(exc, OSError):
        return SmtpSendError("connect_failed")
    return SmtpSendError("unknown")


async def _record(community_id: uuid.UUID | None, error: str | None) -> None:
    """
    @brief Best-effort store of smtp_last_ok_at / smtp_last_error on the community row.

    Writes only when the status flips (ok <-> error), the error text changes, or the
    last success is older than 10 minutes, so a busy mailer doesn't hammer the row.
    """
    if community_id is None:
        return
    from app.db.session import async_session_factory

    try:
        async with async_session_factory() as session:
            row = (
                await session.execute(
                    select(Community.smtp_last_ok_at, Community.smtp_last_error).where(
                        Community.id == community_id
                    )
                )
            ).one_or_none()
            if row is None:
                return
            last_ok, last_err = row
            now = datetime.now(UTC)
            if error is None:
                if last_err is None and last_ok is not None and now - last_ok < _RECORD_REFRESH:
                    return
                values: dict[str, Any] = {"smtp_last_ok_at": now, "smtp_last_error": None}
            else:
                if last_err == error:
                    return
                values = {"smtp_last_error": error}
            await session.execute(
                update(Community).where(Community.id == community_id).values(**values)
            )
            await session.commit()
    except Exception as exc:  # status is informational; never break a send
        logger.warning("smtp_status_record_failed", error=type(exc).__name__)


UNREADABLE_MSG = "Saved password can't be read; re-enter it."


async def _fail(cfg: SmtpConfig, record: bool, err: SmtpSendError, exc: Exception | None) -> None:
    """@brief Log the raw cause (server log only), record the sanitised one, raise it."""
    raw = ""
    if exc is not None:
        raw = f"{type(exc).__name__}: {exc}"
        for secret in (cfg.password, cfg.password.replace(" ", ""), cfg.google_refresh):
            if secret:
                raw = raw.replace(secret, "***")
    logger.error("email_send_failed", category=err.category, host=cfg.host, detail=raw[:500])
    if record:
        await _record(cfg.community_id, err.stored)
    raise err from exc


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
    @throws SmtpSendError sanitised category + message; raw text only goes to the log.
    """
    if cfg.secret_unreadable:
        await _fail(cfg, record, SmtpSendError("auth_failed", UNREADABLE_MSG), None)
    if cfg.security == "none" and (cfg.user or cfg.password):
        await _fail(
            cfg,
            record,
            SmtpSendError("tls_failed", "Refusing to send credentials without encryption"),
            None,
        )
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
        await _fail(cfg, record, classify(exc), exc)
    logger.info("email_sent", to=to, subject=subject)
    if record:
        await _record(cfg.community_id, None)
