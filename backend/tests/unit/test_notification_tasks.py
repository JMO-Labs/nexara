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


class TestSenderNamePassthrough:
    """@brief Branding email_sender_name is passed to EmailSender.send."""

    async def test_passes_branding_sender_name(self):
        import uuid
        from unittest.mock import AsyncMock, MagicMock, patch

        from app.tasks import notification_tasks as nt

        user = MagicMock(email="u@example.com", community_id=uuid.uuid4())
        session = MagicMock()
        session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=user))
        )
        factory = MagicMock()
        factory.return_value.__aenter__ = AsyncMock(return_value=session)
        factory.return_value.__aexit__ = AsyncMock(return_value=None)
        branding = MagicMock(email_sender_name="Silva Family")
        send = AsyncMock(return_value=True)
        with (
            patch.object(nt, "async_session_factory", factory),
            patch.object(nt, "BrandingRepository") as repo,
            patch.object(nt, "EmailSender") as sender_cls,
            patch.object(nt, "EmailTemplateRenderer") as rend,
        ):
            repo.return_value.get = AsyncMock(return_value=branding)
            rend.return_value.render.return_value = ("<p>x</p>", "x")
            sender_cls.return_value.send = send
            await nt._send_email_notification_async(uuid.uuid4(), "comment", {})
        assert send.call_args.kwargs["sender_name"] == "Silva Family"
