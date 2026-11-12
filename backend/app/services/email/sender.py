"""
@file sender.py
@brief Async SMTP email sender with List-Unsubscribe header support.

No-op when SMTP is not configured (SMTP_HOST empty).
"""

from __future__ import annotations

from email.utils import formataddr

import structlog
from aiosmtplib import SMTP

from app.core.config import Settings, get_settings

logger = structlog.get_logger(__name__)


class EmailSender:
    """
    @brief Async email sender using aiosmtplib.

    Skips sending when SMTP_HOST is empty (e.g. local development).
    """

    def __init__(self, settings: Settings | None = None) -> None:
        """
        @brief Initialize the sender.

        @param settings Optional settings; uses get_settings() if not provided.
        """
        self._settings = settings or get_settings()

    async def send(
        self,
        to: str,
        subject: str,
        html_body: str,
        text_body: str | None = None,
        *,
        list_unsubscribe: str | None = None,
        sender_name: str | None = None,
    ) -> bool:
        """
        @brief Send an email via SMTP.

        No-op when SMTP_HOST is empty. Includes List-Unsubscribe header
        when provided.

        @param to Recipient email address.
        @param subject Email subject.
        @param html_body HTML body.
        @param text_body Optional plain-text body.
        @param list_unsubscribe Optional List-Unsubscribe header value.
        @param sender_name Optional display name for the From header.
        @return True if sent, False if skipped (SMTP not configured).
        """
        if not self._settings.SMTP_HOST:
            logger.debug("email_skipped_smtp_not_configured", to=to, subject=subject)
            return False

        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        from_addr = self._settings.SMTP_FROM or "noreply@nexara.local"
        msg["From"] = formataddr((sender_name, from_addr)) if sender_name else from_addr
        msg["To"] = to

        if list_unsubscribe:
            msg["List-Unsubscribe"] = list_unsubscribe

        msg.attach(MIMEText(text_body or html_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        try:
            async with SMTP(
                hostname=self._settings.SMTP_HOST,
                port=self._settings.SMTP_PORT,
                username=self._settings.SMTP_USER or None,
                password=self._settings.SMTP_PASSWORD or None,
                use_tls=True,
            ) as smtp:
                await smtp.send_message(msg)
            logger.info("email_sent", to=to, subject=subject)
            return True
        except Exception as exc:
            logger.exception("email_send_failed", to=to, subject=subject, error=str(exc))
            raise
