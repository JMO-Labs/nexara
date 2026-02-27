"""
@file test_quota.py
@brief Unit tests for storage quota enforcement.

Uses a mock async session to validate check_quota, increment,
decrement, and recalculate logic without a real database.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.storage.quota import (
    QuotaExceededError,
    check_quota,
    decrement_storage_used,
    increment_storage_used,
    recalculate_storage_used,
)

TEN_GB = 10 * 1024**3


def _mock_session_with_user(storage_used: int, storage_quota: int) -> AsyncMock:
    """@brief Build a mock session returning a single user row."""
    session = AsyncMock()
    result = MagicMock()
    result.one_or_none.return_value = (storage_used, storage_quota)
    session.execute.return_value = result
    return session


class TestCheckQuota:
    """@brief Verify pre-upload quota checks."""

    @pytest.mark.asyncio
    async def test_allows_upload_within_quota(self):
        session = _mock_session_with_user(storage_used=0, storage_quota=TEN_GB)
        user_id = uuid.uuid4()
        await check_quota(session, user_id, upload_size=5_000_000)

    @pytest.mark.asyncio
    async def test_allows_upload_exactly_at_limit(self):
        session = _mock_session_with_user(
            storage_used=TEN_GB - 1000,
            storage_quota=TEN_GB,
        )
        user_id = uuid.uuid4()
        await check_quota(session, user_id, upload_size=1000)

    @pytest.mark.asyncio
    async def test_rejects_upload_exceeding_quota(self):
        session = _mock_session_with_user(
            storage_used=TEN_GB - 500,
            storage_quota=TEN_GB,
        )
        user_id = uuid.uuid4()
        with pytest.raises(QuotaExceededError):
            await check_quota(session, user_id, upload_size=1000)

    @pytest.mark.asyncio
    async def test_rejects_upload_when_already_full(self):
        session = _mock_session_with_user(
            storage_used=TEN_GB,
            storage_quota=TEN_GB,
        )
        user_id = uuid.uuid4()
        with pytest.raises(QuotaExceededError):
            await check_quota(session, user_id, upload_size=1)

    @pytest.mark.asyncio
    async def test_raises_value_error_for_missing_user(self):
        session = AsyncMock()
        result = MagicMock()
        result.one_or_none.return_value = None
        session.execute.return_value = result
        with pytest.raises(ValueError, match="not found"):
            await check_quota(session, uuid.uuid4(), upload_size=1)


class TestIncrementStorageUsed:
    """@brief Verify atomic increment calls the correct SQL."""

    @pytest.mark.asyncio
    async def test_executes_update(self):
        session = AsyncMock()
        user_id = uuid.uuid4()
        await increment_storage_used(session, user_id, size_bytes=5_000_000)
        session.execute.assert_called_once()
        call_args = session.execute.call_args
        params = call_args[0][1]
        assert params["size"] == 5_000_000
        assert params["user_id"] == user_id


class TestDecrementStorageUsed:
    """@brief Verify atomic decrement calls the correct SQL."""

    @pytest.mark.asyncio
    async def test_executes_update(self):
        session = AsyncMock()
        user_id = uuid.uuid4()
        await decrement_storage_used(session, user_id, size_bytes=3_000_000)
        session.execute.assert_called_once()
        call_args = session.execute.call_args
        params = call_args[0][1]
        assert params["size"] == 3_000_000
        assert params["user_id"] == user_id


class TestRecalculateStorageUsed:
    """@brief Verify recalculation reads media sum and updates user."""

    @pytest.mark.asyncio
    async def test_returns_actual_usage(self):
        session = AsyncMock()

        select_result = MagicMock()
        select_result.scalar_one.return_value = 42_000_000
        update_result = MagicMock()
        session.execute.side_effect = [select_result, update_result]

        user_id = uuid.uuid4()
        actual = await recalculate_storage_used(session, user_id)

        assert actual == 42_000_000
        assert session.execute.call_count == 2


class TestQuotaExceededError:
    """@brief Verify error message and attributes."""

    def test_error_attributes(self):
        err = QuotaExceededError(quota=TEN_GB, used=TEN_GB - 100, upload_size=200)
        assert err.quota == TEN_GB
        assert err.used == TEN_GB - 100
        assert err.upload_size == 200
        assert "10.0GB quota" in str(err)
