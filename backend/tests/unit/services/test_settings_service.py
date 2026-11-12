"""
@file test_settings_service.py
@brief Unit tests for SettingsService.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.schemas.settings import NotificationPreferences, ProfileUpdate, UserSettingsUpdate
from app.services.settings_service import SettingsService

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
USER_ID = uuid.uuid4()


def _make_settings_row():
    """@brief Create a mock UserSettings ORM object with defaults."""
    row = MagicMock()
    row.user_id = USER_ID
    row.notif_mention_inapp = True
    row.notif_mention_email = True
    row.notif_comment_inapp = True
    row.notif_comment_email = True
    row.notif_reaction_inapp = True
    row.notif_reaction_email = False
    row.notif_new_post_inapp = True
    row.notif_new_post_email = False
    row.notif_system_inapp = True
    row.notif_system_email = True
    row.notif_invite_accepted_inapp = True
    row.notif_invite_accepted_email = False
    row.mute_all_email = False
    row.theme = "system"
    row.locale = "en-US"
    row.home_layout = None
    return row


class TestGetSettings:
    """@brief Tests for SettingsService.get_settings()."""

    @pytest.mark.asyncio
    async def test_returns_settings_with_defaults(self):
        """get_settings should return a UserSettingsResponse with correct fields."""
        mock_settings_repo = AsyncMock()
        mock_settings_repo.get_or_create.return_value = _make_settings_row()
        mock_user_repo = AsyncMock()

        service = SettingsService(mock_settings_repo, mock_user_repo, COMMUNITY_ID)
        result = await service.get_settings(USER_ID)

        assert result.notif_mention_inapp is True
        assert result.theme == "system"
        mock_settings_repo.get_or_create.assert_awaited_once_with(USER_ID, COMMUNITY_ID)


class TestUpdateSettings:
    """@brief Tests for SettingsService.update_settings()."""

    @pytest.mark.asyncio
    async def test_persists_changes(self):
        """update_settings should call repo.update with correct data."""
        mock_settings_repo = AsyncMock()
        mock_settings_repo.get_or_create.return_value = _make_settings_row()
        updated_row = _make_settings_row()
        updated_row.theme = "dark"
        mock_settings_repo.update.return_value = updated_row
        mock_user_repo = AsyncMock()

        service = SettingsService(mock_settings_repo, mock_user_repo, COMMUNITY_ID)
        result = await service.update_settings(USER_ID, UserSettingsUpdate(theme="dark"))

        assert result.theme == "dark"
        mock_settings_repo.update.assert_awaited_once()


class TestUpdateProfile:
    """@brief Tests for SettingsService.update_profile()."""

    @pytest.mark.asyncio
    async def test_updates_user_fields(self):
        """update_profile should update user fields via user_repo."""
        mock_settings_repo = AsyncMock()
        mock_user_repo = AsyncMock()
        mock_user = MagicMock()
        mock_user_repo.get_by_id.return_value = mock_user
        mock_user_repo.update.return_value = mock_user

        service = SettingsService(mock_settings_repo, mock_user_repo, COMMUNITY_ID)
        result = await service.update_profile(
            USER_ID,
            ProfileUpdate(display_name="New Name"),
        )

        assert "display_name" in result
        mock_user_repo.update.assert_awaited_once()


class TestUpdateEmail:
    """@brief Tests for SettingsService.update_email()."""

    @pytest.mark.asyncio
    async def test_logs_email_change_request(self):
        """update_email should succeed without raising when user exists."""
        mock_settings_repo = AsyncMock()
        mock_user_repo = AsyncMock()
        mock_user = MagicMock()
        mock_user_repo.get_by_id.return_value = mock_user

        service = SettingsService(mock_settings_repo, mock_user_repo, COMMUNITY_ID)
        await service.update_email(USER_ID, "new@example.com")

        mock_user_repo.get_by_id.assert_awaited_once_with(USER_ID)

    @pytest.mark.asyncio
    async def test_raises_when_user_not_found(self):
        """update_email should raise ValueError if user does not exist."""
        mock_settings_repo = AsyncMock()
        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_id.return_value = None

        service = SettingsService(mock_settings_repo, mock_user_repo, COMMUNITY_ID)
        with pytest.raises(ValueError, match="User not found"):
            await service.update_email(USER_ID, "new@example.com")


class TestUpdateNotificationPreferences:
    """@brief Tests for SettingsService.update_notification_preferences()."""

    @pytest.mark.asyncio
    async def test_updates_notification_toggles(self):
        """update_notification_preferences should update the correct fields."""
        mock_settings_repo = AsyncMock()
        mock_settings_repo.get_or_create.return_value = _make_settings_row()
        updated_row = _make_settings_row()
        updated_row.notif_mention_email = False
        mock_settings_repo.update.return_value = updated_row
        mock_user_repo = AsyncMock()

        service = SettingsService(mock_settings_repo, mock_user_repo, COMMUNITY_ID)
        result = await service.update_notification_preferences(
            USER_ID,
            NotificationPreferences(notif_mention_email=False),
        )

        assert result.notif_mention_email is False


class TestNudgeOptOuts:
    """@brief receive_nudges / receive_gentle_nudges persist via update_settings (nexara#62)."""

    @pytest.mark.asyncio
    async def test_put_updates_nudge_opt_outs_and_get_returns_them(self):
        """A PUT with nudge toggles reaches the repo and GET reflects them."""
        repo = AsyncMock()
        repo.get_or_create.return_value = _make_settings_row()
        stored = _make_settings_row()
        stored.receive_nudges = False
        stored.receive_gentle_nudges = False
        repo.update.return_value = stored
        service = SettingsService(repo, AsyncMock(), COMMUNITY_ID)

        payload = UserSettingsUpdate(receive_nudges=False, receive_gentle_nudges=False)
        result = await service.update_settings(USER_ID, payload)

        repo.update.assert_awaited_once_with(
            USER_ID, {"receive_nudges": False, "receive_gentle_nudges": False}
        )
        assert result.receive_nudges is False
        assert result.receive_gentle_nudges is False

        repo.get_or_create.return_value = stored
        fetched = await service.get_settings(USER_ID)
        assert fetched.receive_nudges is False
        assert fetched.receive_gentle_nudges is False
