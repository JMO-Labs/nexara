"""
@file test_moderation_repo.py
@brief Unit tests for ModerationRepository.

Tests verify block/report CRUD operations using mocked async sessions.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.moderation import ContentReport, UserBlock
from app.repositories.moderation_repo import ModerationRepository

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
USER_A = uuid.uuid4()
USER_B = uuid.uuid4()


def _make_session() -> AsyncMock:
    """@brief Create a mock AsyncSession with flush/refresh/execute stubs."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    return session


class TestCreateBlock:
    """@brief Tests for ModerationRepository.create_block()."""

    @pytest.mark.asyncio
    async def test_create_block_returns_user_block(self):
        """create_block should persist a UserBlock and return it."""
        session = _make_session()
        repo = ModerationRepository(session)

        result = await repo.create_block(USER_A, USER_B, COMMUNITY_ID)

        assert isinstance(result, UserBlock)
        assert result.blocker_id == USER_A
        assert result.blocked_id == USER_B
        session.add.assert_called_once()
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_block_sets_community_id(self):
        """create_block should set community_id on the block record."""
        session = _make_session()
        repo = ModerationRepository(session)

        result = await repo.create_block(USER_A, USER_B, COMMUNITY_ID)

        assert result.community_id == COMMUNITY_ID


class TestRemoveBlock:
    """@brief Tests for ModerationRepository.remove_block()."""

    @pytest.mark.asyncio
    async def test_remove_block_deletes_record(self):
        """remove_block should execute a DELETE query."""
        session = _make_session()
        session.execute.return_value = MagicMock(rowcount=1)
        repo = ModerationRepository(session)

        await repo.remove_block(USER_A, USER_B)

        session.execute.assert_awaited_once()


class TestIsBlocked:
    """@brief Tests for ModerationRepository.is_blocked()."""

    @pytest.mark.asyncio
    async def test_is_blocked_returns_true_when_block_exists(self):
        """is_blocked should return True when a block record exists."""
        session = _make_session()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock()
        session.execute.return_value = mock_result

        repo = ModerationRepository(session)
        result = await repo.is_blocked(USER_A, USER_B)

        assert result is True

    @pytest.mark.asyncio
    async def test_is_blocked_returns_false_when_no_block(self):
        """is_blocked should return False when no block record exists."""
        session = _make_session()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute.return_value = mock_result

        repo = ModerationRepository(session)
        result = await repo.is_blocked(USER_A, USER_B)

        assert result is False


class TestGetBlockedUserIds:
    """@brief Tests for ModerationRepository.get_blocked_user_ids()."""

    @pytest.mark.asyncio
    async def test_returns_set_of_blocked_ids(self):
        """get_blocked_user_ids should return a set of blocked user UUIDs."""
        blocked_1 = uuid.uuid4()
        blocked_2 = uuid.uuid4()

        session = _make_session()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [blocked_1, blocked_2]
        session.execute.return_value = mock_result

        repo = ModerationRepository(session)
        result = await repo.get_blocked_user_ids(USER_A)

        assert result == {blocked_1, blocked_2}

    @pytest.mark.asyncio
    async def test_returns_empty_set_when_no_blocks(self):
        """get_blocked_user_ids should return an empty set when no blocks exist."""
        session = _make_session()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        session.execute.return_value = mock_result

        repo = ModerationRepository(session)
        result = await repo.get_blocked_user_ids(USER_A)

        assert result == set()


class TestCreateReport:
    """@brief Tests for ModerationRepository.create_report()."""

    @pytest.mark.asyncio
    async def test_create_report_returns_content_report(self):
        """create_report should persist a ContentReport and return it."""
        session = _make_session()
        repo = ModerationRepository(session)

        result = await repo.create_report(
            reporter_id=USER_A,
            target_type="post",
            target_id=uuid.uuid4(),
            reason="spam",
            description="This is spam content",
            community_id=COMMUNITY_ID,
        )

        assert isinstance(result, ContentReport)
        assert result.reporter_id == USER_A
        assert result.reason == "spam"
        assert result.status == "pending"
        session.add.assert_called_once()
        session.flush.assert_awaited_once()


class TestListReports:
    """@brief Tests for ModerationRepository.list_reports()."""

    @pytest.mark.asyncio
    async def test_list_reports_returns_reports_and_cursor(self):
        """list_reports should return a list of reports and a next_cursor."""
        report = MagicMock(spec=ContentReport)
        report.id = uuid.uuid4()
        report.created_at = datetime.now(UTC)

        session = _make_session()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [report]
        session.execute.return_value = mock_result

        repo = ModerationRepository(session)
        reports, cursor = await repo.list_reports(limit=10)

        session.execute.assert_awaited_once()
        assert len(reports) == 1
        assert cursor is None


class TestSetNsfw:
    """@brief Tests for ModerationRepository.set_nsfw()."""

    @staticmethod
    def _session(found: bool) -> AsyncMock:
        session = _make_session()
        result = MagicMock()
        result.scalar_one_or_none.return_value = uuid.uuid4() if found else None
        session.execute.return_value = result
        return session

    @pytest.mark.asyncio
    async def test_posts_update_excludes_soft_deleted(self):
        session = self._session(True)
        assert await ModerationRepository(session).set_nsfw("posts", uuid.uuid4(), COMMUNITY_ID)
        sql = str(session.execute.await_args.args[0])
        assert "UPDATE posts" in sql
        assert "deleted_at IS NULL" in sql
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_media_update_has_no_soft_delete_filter(self):
        session = self._session(True)
        assert await ModerationRepository(session).set_nsfw("media", uuid.uuid4(), COMMUNITY_ID)
        sql = str(session.execute.await_args.args[0])
        assert "UPDATE media" in sql
        assert "deleted_at" not in sql

    @pytest.mark.asyncio
    async def test_returns_false_when_no_row(self):
        session = self._session(False)
        assert not await ModerationRepository(session).set_nsfw("posts", uuid.uuid4(), COMMUNITY_ID)

    @pytest.mark.asyncio
    async def test_unsupported_kind_raises(self):
        session = self._session(True)
        with pytest.raises(ValueError, match="unsupported kind"):
            await ModerationRepository(session).set_nsfw("users", uuid.uuid4(), COMMUNITY_ID)
        session.execute.assert_not_awaited()
