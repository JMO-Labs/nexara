"""
@file test_notification_service.py
@brief Unit tests for NotificationService.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.notification import Notification
from app.services.notification_service import NotificationService

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
USER_ID = uuid.uuid4()


def _make_settings(inapp: bool = True, email: bool = False, mute_all: bool = False):
    """@brief Create mock UserSettings with given prefs."""
    row = MagicMock()
    row.notif_mention_inapp = inapp
    row.notif_mention_email = email
    row.notif_comment_inapp = inapp
    row.notif_comment_email = email
    row.notif_reaction_inapp = inapp
    row.notif_reaction_email = email
    row.notif_new_post_inapp = inapp
    row.notif_new_post_email = email
    row.notif_system_inapp = inapp
    row.notif_system_email = email
    row.notif_invite_accepted_inapp = inapp
    row.notif_invite_accepted_email = email
    row.mute_all_email = mute_all
    return row


class TestNotifyInApp:
    """@brief Tests for notify() in-app channel."""

    @pytest.mark.asyncio
    async def test_creates_db_record_when_inapp_enabled(self):
        """notify() creates DB record when in-app is enabled."""
        mock_notif_repo = AsyncMock()
        mock_settings_repo = AsyncMock()
        mock_settings_repo.get_or_create.return_value = _make_settings(inapp=True)
        notif = Notification(
            id=uuid.uuid4(),
            user_id=USER_ID,
            community_id=COMMUNITY_ID,
            type="mention",
            payload={"message": "Hello"},
        )
        mock_notif_repo.create.return_value = notif

        service = NotificationService(
            mock_notif_repo,
            mock_settings_repo,
            COMMUNITY_ID,
        )
        result = await service.notify(USER_ID, "mention", {"message": "Hello"})

        assert result is not None
        mock_notif_repo.create.assert_awaited_once()
        call_args = mock_notif_repo.create.call_args[0]
        assert call_args[0] == USER_ID
        assert call_args[1] == "mention"
        assert call_args[2] == {"message": "Hello"}

    @pytest.mark.asyncio
    async def test_skips_db_record_when_inapp_disabled(self):
        """notify() skips DB record when in-app is disabled."""
        mock_notif_repo = AsyncMock()
        mock_settings_repo = AsyncMock()
        mock_settings_repo.get_or_create.return_value = _make_settings(inapp=False)

        service = NotificationService(
            mock_notif_repo,
            mock_settings_repo,
            COMMUNITY_ID,
        )
        with patch("app.tasks.notification_tasks.send_email_notification") as mock_task:
            mock_task.delay = MagicMock()
            result = await service.notify(USER_ID, "mention", {"message": "Hi"})

        assert result is None
        mock_notif_repo.create.assert_not_awaited()


class TestNotifyEmail:
    """@brief Tests for notify() email channel."""

    @pytest.mark.asyncio
    async def test_enqueues_email_when_email_channel_enabled(self):
        """notify() enqueues email task when email channel is enabled."""
        mock_notif_repo = AsyncMock()
        mock_settings_repo = AsyncMock()
        mock_settings_repo.get_or_create.return_value = _make_settings(
            inapp=True,
            email=True,
            mute_all=False,
        )
        notif = Notification(
            id=uuid.uuid4(),
            user_id=USER_ID,
            community_id=COMMUNITY_ID,
            type="comment",
            payload={"message": "New comment"},
        )
        mock_notif_repo.create.return_value = notif

        service = NotificationService(
            mock_notif_repo,
            mock_settings_repo,
            COMMUNITY_ID,
        )
        with patch("app.tasks.notification_tasks.send_email_notification") as mock_task:
            mock_task.delay = MagicMock()
            await service.notify(USER_ID, "comment", {"message": "New comment"})

        mock_task.delay.assert_called_once()
        call_args = mock_task.delay.call_args[0]
        assert call_args[0] == str(USER_ID)
        assert call_args[1] == "comment"
        assert call_args[2]["message"] == "New comment"

    @pytest.mark.asyncio
    async def test_skips_email_when_mute_all_email(self):
        """notify() skips email when mute_all_email is True."""
        mock_notif_repo = AsyncMock()
        mock_settings_repo = AsyncMock()
        mock_settings_repo.get_or_create.return_value = _make_settings(
            inapp=True,
            email=True,
            mute_all=True,
        )
        notif = Notification(
            id=uuid.uuid4(),
            user_id=USER_ID,
            community_id=COMMUNITY_ID,
            type="comment",
            payload={},
        )
        mock_notif_repo.create.return_value = notif

        service = NotificationService(
            mock_notif_repo,
            mock_settings_repo,
            COMMUNITY_ID,
        )
        with patch("app.tasks.notification_tasks.send_email_notification") as mock_task:
            mock_task.delay = MagicMock()
            await service.notify(USER_ID, "comment", {"message": "Hi"})

        mock_task.delay.assert_not_called()
