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
