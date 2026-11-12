"""
@file test_gallery_tasks.py
@brief Unit tests for gallery reminder and notification tasks.
"""

import uuid
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

from tests.unit.services.strict_notify import strict_notify

from app.tasks.gallery_tasks import gallery_batch_notifications, gallery_post_event_reminders


class TestGalleryPostEventReminders:
    """@brief Verify post-event reminder task."""

    def test_task_name(self):
        assert (
            gallery_post_event_reminders.name
            == "app.tasks.gallery_tasks.gallery_post_event_reminders"
        )

    def test_queue_is_notifications(self):
        assert gallery_post_event_reminders.queue == "notifications"

    @pytest.mark.asyncio
    async def test_post_event_reminders_notifies_attendees(self):
        """Events ending in last 24h with attendees notify each attendee."""
        event_id = uuid.uuid4()
        gallery_id = uuid.uuid4()
        attendee1_id = uuid.uuid4()
        attendee2_id = uuid.uuid4()

        mock_event = MagicMock()
        mock_event.id = event_id
        mock_event.title = "Test Event"
        mock_event.community_id = uuid.uuid4()

        mock_gallery = MagicMock()
        mock_gallery.title = "Test Gallery"
        mock_gallery.id = gallery_id

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        mock_event_repo = AsyncMock()
        mock_event_repo.list_ended_in_window.return_value = [mock_event]
        mock_event_repo.list_attendees.return_value = [attendee1_id, attendee2_id]

        mock_gallery_repo = AsyncMock()
        mock_gallery_repo.get_event_gallery.return_value = mock_gallery

        mock_notif = AsyncMock()
        mock_notif.notify = strict_notify().notify

        with (
            patch("app.tasks.gallery_tasks.async_session_factory") as mock_factory,
            patch("app.tasks.gallery_tasks.EventRepository", return_value=mock_event_repo),
            patch("app.tasks.gallery_tasks.GalleryRepository", return_value=mock_gallery_repo),
            patch("app.tasks.gallery_tasks.NotificationService", return_value=mock_notif),
            patch("app.tasks.gallery_tasks.NotificationRepository"),
            patch("app.tasks.gallery_tasks.SettingsRepository"),
        ):

            async def mock_context():
                return mock_session

            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)

            from app.tasks.gallery_tasks import _post_event_reminders

            result = await _post_event_reminders()

            assert result == {"sent": 2}
            assert mock_notif.notify.call_count == 2
            mock_notif.notify.assert_any_call(
                user_id=attendee1_id,
                type="gallery_reminder",
                payload=ANY,
            )

    @pytest.mark.asyncio
    async def test_post_event_reminders_skips_events_without_gallery(self):
        """Events without gallery are skipped."""
        event_id = uuid.uuid4()

        mock_event = MagicMock()
        mock_event.id = event_id

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        mock_event_repo = AsyncMock()
        mock_event_repo.list_ended_in_window.return_value = [mock_event]
        mock_event_repo.list_attendees.return_value = []

        mock_gallery_repo = AsyncMock()
        mock_gallery_repo.get_event_gallery.return_value = None

        mock_notif = AsyncMock()
        mock_notif.notify = strict_notify().notify

        with (
            patch("app.tasks.gallery_tasks.async_session_factory") as mock_factory,
            patch("app.tasks.gallery_tasks.EventRepository", return_value=mock_event_repo),
            patch("app.tasks.gallery_tasks.GalleryRepository", return_value=mock_gallery_repo),
            patch("app.tasks.gallery_tasks.NotificationService", return_value=mock_notif),
            patch("app.tasks.gallery_tasks.NotificationRepository"),
            patch("app.tasks.gallery_tasks.SettingsRepository"),
        ):
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)

            from app.tasks.gallery_tasks import _post_event_reminders

            result = await _post_event_reminders()

            assert result == {"sent": 0}
            assert mock_notif.notify.call_count == 0


class TestGalleryBatchNotifications:
    """@brief Verify gallery batch notification task."""

    def test_task_name(self):
        assert (
            gallery_batch_notifications.name
            == "app.tasks.gallery_tasks.gallery_batch_notifications"
        )

    def test_queue_is_notifications(self):
        assert gallery_batch_notifications.queue == "notifications"

    @pytest.mark.asyncio
    async def test_batch_notifications_for_active_galleries(self):
        """Galleries with ≥5 new items in last 60min notify subscribers."""
        gallery_id = uuid.uuid4()
        subscriber1_id = uuid.uuid4()
        subscriber2_id = uuid.uuid4()

        mock_gallery = MagicMock()
        mock_gallery.title = "Test Gallery"
        mock_gallery.id = gallery_id
        mock_gallery.community_id = uuid.uuid4()

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        mock_gallery_repo = AsyncMock()
        mock_gallery_repo.list_with_recent_activity.return_value = [(mock_gallery, 7)]
        mock_gallery_repo.list_subscribers.return_value = [subscriber1_id, subscriber2_id]

        mock_notif = AsyncMock()
        mock_notif.notify = strict_notify().notify

        with (
            patch("app.tasks.gallery_tasks.async_session_factory") as mock_factory,
            patch("app.tasks.gallery_tasks.GalleryRepository", return_value=mock_gallery_repo),
            patch("app.tasks.gallery_tasks.NotificationService", return_value=mock_notif),
            patch("app.tasks.gallery_tasks.NotificationRepository"),
            patch("app.tasks.gallery_tasks.SettingsRepository"),
        ):
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)

            from app.tasks.gallery_tasks import _batch_notifications

            result = await _batch_notifications()

            assert result == {"sent": 2}
            assert mock_notif.notify.call_count == 2
            mock_notif.notify.assert_any_call(
                user_id=subscriber1_id,
                type="gallery_activity",
                payload=ANY,
            )

    @pytest.mark.asyncio
    async def test_batch_notifications_no_active_galleries(self):
        """No galleries with activity returns sent=0."""
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        mock_gallery_repo = AsyncMock()
        mock_gallery_repo.list_with_recent_activity.return_value = []

        mock_notif = AsyncMock()
        mock_notif.notify = strict_notify().notify

        with (
            patch("app.tasks.gallery_tasks.async_session_factory") as mock_factory,
            patch("app.tasks.gallery_tasks.GalleryRepository", return_value=mock_gallery_repo),
            patch("app.tasks.gallery_tasks.NotificationService", return_value=mock_notif),
            patch("app.tasks.gallery_tasks.NotificationRepository"),
            patch("app.tasks.gallery_tasks.SettingsRepository"),
        ):
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)

            from app.tasks.gallery_tasks import _batch_notifications

            result = await _batch_notifications()

            assert result == {"sent": 0}
            assert mock_notif.notify.call_count == 0
