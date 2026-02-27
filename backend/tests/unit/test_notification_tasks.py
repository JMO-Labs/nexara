"""
@file test_notification_tasks.py
@brief Unit tests for notification tasks.
"""

from app.tasks.notification_tasks import (
    dispatch_event_reminders,
    send_email_notification,
    send_push_notification,
)


class TestSendPushNotification:
    """@brief Verify push notification task configuration."""

    def test_task_name(self):
        assert send_push_notification.name == "app.tasks.notification_tasks.send_push_notification"

    def test_queue_is_notifications(self):
        assert send_push_notification.queue == "notifications"

    def test_returns_status(self):
        result = send_push_notification("fake-user-id", {"title": "Test"})
        assert result["status"] == "sent"


class TestSendEmailNotification:
    """@brief Verify email notification task configuration."""

    def test_task_name(self):
        assert (
            send_email_notification.name == "app.tasks.notification_tasks.send_email_notification"
        )

    def test_returns_error_for_invalid_uuid(self):
        """Invalid UUID strings should return error status without raising."""
        result = send_email_notification("fake-user-id", "comment", {"post_id": "123"})
        assert result["status"] == "error"


class TestDispatchEventReminders:
    """@brief Verify event reminder dispatch task."""

    def test_task_name(self):
        assert (
            dispatch_event_reminders.name == "app.tasks.notification_tasks.dispatch_event_reminders"
        )

    def test_returns_count(self):
        result = dispatch_event_reminders()
        assert "reminders_sent" in result
