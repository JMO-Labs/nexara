"""
@file test_email_tasks.py
@brief Unit tests for email tasks.
"""

from unittest.mock import patch

from app.tasks.email_tasks import send_email, send_invite_email, send_password_reset_email


class TestSendEmail:
    """@brief Verify the send_email task."""

    def test_skips_when_smtp_not_configured(self):
        with patch("app.tasks.email_tasks._smtp_configured", return_value=False):
            result = send_email("test@example.com", "Subject", "<p>Body</p>")
            assert result["status"] == "skipped"

    def test_task_name(self):
        assert send_email.name == "app.tasks.email_tasks.send_email"

    def test_queue_is_email(self):
        assert send_email.queue == "email"


class TestSendInviteEmail:
    """@brief Verify the invite email task."""

    def test_skips_when_smtp_not_configured(self):
        with patch("app.tasks.email_tasks._smtp_configured", return_value=False):
            result = send_invite_email("fake-invite-id")
            assert result["status"] == "skipped"

    def test_task_name(self):
        assert send_invite_email.name == "app.tasks.email_tasks.send_invite_email"


class TestSendPasswordResetEmail:
    """@brief Verify the password reset email task."""

    def test_skips_when_smtp_not_configured(self):
        with patch("app.tasks.email_tasks._smtp_configured", return_value=False):
            result = send_password_reset_email("fake-user-id", "fake-token")
            assert result["status"] == "skipped"

    def test_task_name(self):
        assert send_password_reset_email.name == "app.tasks.email_tasks.send_password_reset_email"
