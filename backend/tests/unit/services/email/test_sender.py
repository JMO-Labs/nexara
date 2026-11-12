"""
@file test_sender.py
@brief Unit tests for EmailSender.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.email.sender import EmailSender


class TestSendConfigured:
    """@brief Tests when SMTP is configured."""

    @pytest.mark.asyncio
    async def test_send_calls_smtp_with_correct_args(self):
        """send() calls aiosmtplib SMTP with correct arguments."""
        mock_settings = MagicMock()
        mock_settings.SMTP_HOST = "smtp.example.com"
        mock_settings.SMTP_PORT = 587
        mock_settings.SMTP_USER = "user"
        mock_settings.SMTP_PASSWORD = "secret"
        mock_settings.SMTP_FROM = "noreply@example.com"

        sender = EmailSender(settings=mock_settings)

        mock_ctx = MagicMock()
        mock_ctx.send_message = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.email.sender.SMTP", return_value=mock_ctx) as mock_smtp:
            result = await sender.send(
                to="user@example.com",
                subject="Test",
                html_body="<p>Hello</p>",
                text_body="Hello",
            )

            assert result is True
            mock_smtp.assert_called_once()
            call_kw = mock_smtp.call_args.kwargs
            assert call_kw["hostname"] == "smtp.example.com"
            assert call_kw["port"] == 587


class TestSendNotConfigured:
    """@brief Tests when SMTP is not configured."""

    @pytest.mark.asyncio
    async def test_send_is_noop_when_smtp_not_configured(self):
        """send() is a no-op when SMTP_HOST is empty."""
        mock_settings = MagicMock()
        mock_settings.SMTP_HOST = ""
        mock_settings.SMTP_FROM = ""

        sender = EmailSender(settings=mock_settings)

        with patch("app.services.email.sender.SMTP", new_callable=AsyncMock) as mock_smtp:
            result = await sender.send(
                to="user@example.com",
                subject="Test",
                html_body="<p>Hello</p>",
            )

            assert result is False
            mock_smtp.assert_not_called()


def _send_with_name(sender_name):
    """@brief Send one mail and return the captured message."""
    settings = MagicMock()
    settings.SMTP_HOST = "smtp.example.com"
    settings.SMTP_PORT = 587
    settings.SMTP_USER = ""
    settings.SMTP_PASSWORD = ""
    settings.SMTP_FROM = "noreply@example.com"
    ctx = MagicMock()
    ctx.send_message = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=ctx)
    ctx.__aexit__ = AsyncMock(return_value=None)
    return settings, ctx


class TestSenderName:
    """@brief From header display name handling."""

    @pytest.mark.asyncio
    async def test_sender_name_sets_display_name(self):
        settings, ctx = _send_with_name("Família Silva")
        with patch("app.services.email.sender.SMTP", return_value=ctx):
            await EmailSender(settings=settings).send(
                "u@example.com", "S", "<p>x</p>", sender_name="Família Silva"
            )
        from email.utils import formataddr

        msg = ctx.send_message.call_args.args[0]
        assert msg["From"] == formataddr(("Família Silva", "noreply@example.com"))
        assert "noreply@example.com" in msg["From"]

    @pytest.mark.asyncio
    async def test_no_sender_name_keeps_plain_from(self):
        settings, ctx = _send_with_name(None)
        with patch("app.services.email.sender.SMTP", return_value=ctx):
            await EmailSender(settings=settings).send("u@example.com", "S", "<p>x</p>")
        assert ctx.send_message.call_args.args[0]["From"] == "noreply@example.com"
