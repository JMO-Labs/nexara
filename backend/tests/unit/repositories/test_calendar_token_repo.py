"""
@file test_calendar_token_repo.py
@brief Unit tests for CalendarTokenRepository.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.calendar_token import CalendarToken
from app.repositories.calendar_token_repo import CalendarTokenRepository


def _make_session() -> AsyncMock:
    """@brief Create a mock AsyncSession with flush/refresh/execute stubs."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    return session


class TestIssueAndVerify:
    """@brief Tests for CalendarTokenRepository.issue() and verify()."""

    @pytest.mark.asyncio
    async def test_issue_and_verify(self):
        """issue should create token and verify should retrieve by raw value."""
        session = _make_session()
        user_id = uuid.uuid4()

        # Mock the issue flow: after add + flush, the model has an id
        async def after_flush():
            pass

        session.flush.side_effect = after_flush

        repo = CalendarTokenRepository(session)
        raw, model = await repo.issue(user_id=user_id, scope="ical")

        assert isinstance(raw, str) and len(raw) >= 32
        assert model.token_hash != raw  # stored hashed
        session.add.assert_called_once()
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_verify_found(self):
        """verify should return model when token hash matches and not revoked."""
        user_id = uuid.uuid4()
        token_id = uuid.uuid4()
        session = _make_session()

        token_model = MagicMock(spec=CalendarToken)
        token_model.id = token_id
        token_model.user_id = user_id
        token_model.scope = "ical"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = token_model
        session.execute.return_value = mock_result

        repo = CalendarTokenRepository(session)
        found = await repo.verify("some-raw-token")

        assert found is not None
        assert found.id == token_id
        session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_verify_not_found(self):
        """verify should return None when token not found or revoked."""
        session = _make_session()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute.return_value = mock_result

        repo = CalendarTokenRepository(session)
        found = await repo.verify("bad-token")

        assert found is None

    @pytest.mark.asyncio
    async def test_revoke(self):
        """revoke should update revoked_at timestamp."""
        session = _make_session()
        token_id = uuid.uuid4()

        repo = CalendarTokenRepository(session)
        await repo.revoke(token_id)

        session.execute.assert_awaited_once()
