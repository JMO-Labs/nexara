"""
@file test_startup.py
@brief Unit tests for startup and seeding functions in main.py.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.config import Settings
from app.models.subgroup import ChatChannel


@pytest.fixture
def settings() -> Settings:
    """@brief Mock Settings object."""
    s = MagicMock(spec=Settings)
    s.COMMUNITY_ID = "00000000-0000-0000-0000-000000000001"
    s.OIDC_ISSUER = None
    return s


class TestSeedDefaultChatChannel:
    """@brief Tests for _seed_default_chat_channel() startup hook."""

    @pytest.mark.asyncio
    async def test_seeds_default_channel_on_startup(self, settings: Settings) -> None:
        """_seed_default_chat_channel creates the default General channel."""
        from app.main import _seed_default_chat_channel

        with patch("app.main.async_session_factory") as mock_factory:
            mock_session = AsyncMock()
            mock_factory.return_value.__aenter__.return_value = mock_session

            with patch("app.repositories.chat_repo.ChatChannelRepository") as mock_repo_cls:
                mock_repo = AsyncMock()
                mock_repo_cls.return_value = mock_repo
                mock_repo.get_or_create_community_default = AsyncMock(
                    return_value=(MagicMock(spec=ChatChannel), True)
                )

                await _seed_default_chat_channel(settings)

                # Verify the repo was instantiated and called
                mock_repo_cls.assert_called_once_with(mock_session)
                mock_repo.get_or_create_community_default.assert_awaited_once_with(
                    uuid.UUID(settings.COMMUNITY_ID)
                )
                mock_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_handles_seed_failure_gracefully(self, settings: Settings) -> None:
        """_seed_default_chat_channel logs failures without raising."""
        from app.main import _seed_default_chat_channel

        with patch("app.main.async_session_factory") as mock_factory:
            mock_factory.side_effect = Exception("DB error")

            with patch("app.main.logger") as mock_logger:
                # Should not raise; should log warning
                await _seed_default_chat_channel(settings)
                mock_logger.warning.assert_called_once()
                call_args = mock_logger.warning.call_args
                assert "seed_default_chat_channel_failed" in str(call_args)


class TestLoadPlugins:
    """@brief Tests for _load_plugins() startup hook."""

    @pytest.mark.asyncio
    async def test_failure_logged_without_raising(self, settings: Settings) -> None:
        """_load_plugins swallows loader errors and logs a warning."""
        from app.main import _load_plugins

        with (
            patch("app.main.async_session_factory") as mock_factory,
            patch("app.plugins.loader.load_plugins", side_effect=RuntimeError("boom")),
            patch("app.main.logger") as mock_logger,
        ):
            mock_factory.return_value.__aenter__.return_value = AsyncMock()
            await _load_plugins(MagicMock(), settings)
            mock_logger.warning.assert_called_once()
            assert "plugins_load_failed" in str(mock_logger.warning.call_args)
