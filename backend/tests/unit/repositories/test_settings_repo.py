"""
@file test_settings_repo.py
@brief Unit tests for SettingsRepository.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.user_settings import UserSettings
from app.repositories.settings_repo import SettingsRepository

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
USER_ID = uuid.uuid4()


def _make_session() -> AsyncMock:
    """@brief Create a mock AsyncSession."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    return session


class TestGetOrCreate:
    """@brief Tests for SettingsRepository.get_or_create()."""

    @pytest.mark.asyncio
    async def test_creates_row_on_first_call(self):
        """get_or_create should create a new row when none exists."""
        session = _make_session()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute.return_value = mock_result

        repo = SettingsRepository(session)
        result = await repo.get_or_create(USER_ID, COMMUNITY_ID)

        assert isinstance(result, UserSettings)
        assert result.user_id == USER_ID
        session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_existing_on_second_call(self):
        """get_or_create should return the existing row without insert."""
        session = _make_session()
        existing = MagicMock(spec=UserSettings)
        existing.user_id = USER_ID
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        session.execute.return_value = mock_result

        repo = SettingsRepository(session)
        result = await repo.get_or_create(USER_ID, COMMUNITY_ID)

        assert result is existing
        session.add.assert_not_called()


class TestCountSassybotOptOuts:
    """@brief Tests for SettingsRepository.count_sassybot_opt_outs()."""

    @pytest.mark.asyncio
    async def test_returns_count_scoped_to_community(self):
        session = _make_session()
        result = MagicMock()
        result.scalar_one.return_value = 4
        session.execute.return_value = result

        count = await SettingsRepository(session).count_sassybot_opt_outs(COMMUNITY_ID)

        assert count == 4
        stmt = session.execute.await_args.args[0]
        assert "allow_sassybot IS false" in str(stmt)
