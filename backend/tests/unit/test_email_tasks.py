"""
@file test_email_tasks.py
@brief Unit tests for email tasks.
"""

from unittest.mock import AsyncMock, MagicMock, patch

from app.tasks.email_tasks import send_email, send_invite_email, send_password_reset_email


class TestSendEmail:
    """@brief Verify the send_email task."""

    def x(self):
        with patch("app.tasks.email_tasks._resolve", AsyncMock(return_value=None)):
            result = send_email("test@example.com", "Subject", "<p>Body</p>")
            assert result["status"] == "skipped"

    def test_sends_through_single_sender(self):
        cfg = MagicMock()
        with (
            patch("app.tasks.email_tasks._resolve", AsyncMock(return_value=cfg)),
            patch("app.tasks.email_tasks.smtp_send", AsyncMock()) as send,
        ):
            result = send_email("a@b.c", "S", "<p>B</p>", "B")
        assert result["status"] == "sent"
        send.assert_awaited_once_with(cfg, "a@b.c", "S", "<p>B</p>", "B")

    def test_task_name(self):
        assert send_email.name == "app.tasks.email_tasks.send_email"

    def test_queue_is_email(self):
        assert send_email.queue == "email"


class TestSendInviteEmail:
    """@brief Verify the invite email task."""

    def test_task_name(self):
        assert send_invite_email.name == "app.tasks.email_tasks.send_invite_email"


class TestSendPasswordResetEmail:
    """@brief Verify the password reset email task."""

    def test_task_name(self):
        assert send_password_reset_email.name == "app.tasks.email_tasks.send_password_reset_email"
