"""
@file test_notification_tasks.py
@brief Unit tests for notification tasks.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from app.tasks.event_tasks import dispatch_event_reminders
from app.tasks.notification_tasks import (
    _send_push_async,
    send_email_notification,
    send_push_notification,
)


class TestSendPushNotification:
    """@brief Verify push notification task configuration."""

    def test_task_name(self):
        assert send_push_notification.name == "app.tasks.notification_tasks.send_push_notification"

    def test_queue_is_notifications(self):
        assert send_push_notification.queue == "notifications"


class TestSendPushAsync:
    """@brief Verify session commit and tenant id in the push task."""

    async def test_commits_and_uses_community_id(self):
        uid, cid = uuid.uuid4(), uuid.uuid4()
        session = AsyncMock()
        session.scalar.return_value = cid
        factory = MagicMock()
        factory.return_value.__aenter__.return_value = session
        with (
            patch("app.tasks.notification_tasks.async_session_factory", factory),
            patch("app.tasks.notification_tasks.PushSubscriptionRepository") as repo,
            patch("app.tasks.notification_tasks.SettingsRepository"),
            patch("app.tasks.notification_tasks.PushService") as svc,
        ):
            repo.return_value.list_for_user = AsyncMock(return_value=[object()])
            svc.return_value.send_push = AsyncMock()
            result = await _send_push_async(uid, {"title": "t"})
        assert result == {"status": "sent", "count": 1}
        session.commit.assert_awaited_once()
        assert svc.call_args.args[2] == cid
        assert svc.call_args.args[2] != uid


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
        assert dispatch_event_reminders.name == "app.tasks.event_tasks.dispatch_event_reminders"

    def test_queue_is_notifications(self):
        assert dispatch_event_reminders.queue == "notifications"
