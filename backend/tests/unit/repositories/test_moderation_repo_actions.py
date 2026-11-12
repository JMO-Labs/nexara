"""
@file test_moderation_repo_actions.py
@brief Unit tests for ModerationRepository admin-action and lookup helpers.

Verifies community scoping, per-target hide/delete behaviour and the
(created_at, id) keyset cursor using mocked async sessions.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.dialects import postgresql

from app.models.moderation import ContentReport, UserBlock
from app.repositories.moderation_repo import (
    ModerationRepository,
    decode_report_cursor,
    encode_report_cursor,
)

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
TARGET_ID = uuid.uuid4()
USER_ID = uuid.uuid4()


def _session(result: MagicMock | None = None) -> AsyncMock:
    """@brief Mock AsyncSession whose execute() returns ``result``."""
    session = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock(return_value=result or MagicMock(rowcount=1))
    return session


def _sql(session: AsyncMock) -> str:
    """@brief Render the last executed statement as SQL text."""
    stmt = session.execute.call_args.args[0]
    return str(stmt.compile(dialect=postgresql.dialect())).lower()


def _scalar(value: object) -> MagicMock:
    res = MagicMock()
    res.scalar_one_or_none.return_value = value
    return res


class TestContentLookup:
    async def test_author_id_scoped_to_community(self):
        session = _session(_scalar(USER_ID))
        repo = ModerationRepository(session)
        assert await repo.get_content_author_id("post", TARGET_ID, COMMUNITY_ID) == USER_ID
        sql = _sql(session)
        assert "posts.community_id" in sql and "posts.id" in sql

    @pytest.mark.parametrize(
        ("target_type", "table"),
        [
            ("post", "posts"),
            ("comment", "comments"),
            ("message", "chat_messages"),
            ("media", "media"),
        ],
    )
    async def test_content_exists_scoped(self, target_type, table):
        session = _session(_scalar(TARGET_ID))
        repo = ModerationRepository(session)
        assert await repo.content_exists(target_type, TARGET_ID, COMMUNITY_ID) is True
        assert f"{table}.community_id" in _sql(session)

    async def test_content_exists_false_when_missing(self):
        repo = ModerationRepository(_session(_scalar(None)))
        assert await repo.content_exists("comment", TARGET_ID, COMMUNITY_ID) is False

    async def test_user_exists_scoped(self):
        session = _session(_scalar(USER_ID))
        repo = ModerationRepository(session)
        assert await repo.user_exists(USER_ID, COMMUNITY_ID) is True
        sql = _sql(session)
        assert "users.community_id" in sql and "users.deleted_at is null" in sql

    async def test_user_exists_false(self):
        repo = ModerationRepository(_session(_scalar(None)))
        assert await repo.user_exists(USER_ID, COMMUNITY_ID) is False


class TestRemoveContent:
    async def test_post_is_soft_deleted(self):
        session = _session()
        await ModerationRepository(session).soft_delete_content("post", TARGET_ID, COMMUNITY_ID)
        sql = _sql(session)
        assert sql.startswith("update posts") and "deleted_at" in sql
        assert "posts.community_id" in sql

    @pytest.mark.parametrize(
        ("target_type", "table"),
        [("comment", "comments"), ("message", "chat_messages"), ("media", "media")],
    )
    async def test_models_without_deleted_at_are_hard_deleted(self, target_type, table):
        session = _session()
        await ModerationRepository(session).soft_delete_content(
            target_type, TARGET_ID, COMMUNITY_ID
        )
        sql = _sql(session)
        assert sql.startswith(f"delete from {table}")
        assert f"{table}.community_id" in sql

    async def test_deactivate_user_scoped(self):
        session = _session()
        await ModerationRepository(session).deactivate_user(USER_ID, COMMUNITY_ID)
        sql = _sql(session)
        assert sql.startswith("update users") and "users.community_id" in sql


class TestReportLookups:
    async def test_get_report_scoped(self):
        report = MagicMock(spec=ContentReport)
        session = _session(_scalar(report))
        assert await ModerationRepository(session).get_report(TARGET_ID, COMMUNITY_ID) is report
        assert "content_reports.community_id" in _sql(session)

    async def test_mark_reviewed_sets_fields(self):
        session = _session()
        report = MagicMock(spec=ContentReport)
        out = await ModerationRepository(session).mark_reviewed(
            report,
            status="reviewed",
            action_taken="warn_user",
            admin_notes="n",
            reviewed_by=USER_ID,
        )
        assert out is report
        assert report.status == "reviewed" and report.action_taken == "warn_user"
        assert report.reviewed_by == USER_ID and report.reviewed_at is not None
        session.flush.assert_awaited_once()

    async def test_list_blocks_scoped_and_ordered(self):
        block = MagicMock(spec=UserBlock)
        res = MagicMock()
        res.scalars.return_value.all.return_value = [block]
        session = _session(res)
        assert await ModerationRepository(session).list_blocks(USER_ID, COMMUNITY_ID) == [block]
        sql = _sql(session)
        assert "user_blocks.community_id" in sql and "order by user_blocks.created_at desc" in sql


def _reports(n: int) -> list[MagicMock]:
    now = datetime.now(UTC)
    out = []
    for i in range(n):
        r = MagicMock(spec=ContentReport)
        r.id = uuid.uuid4()
        r.created_at = now - timedelta(minutes=i)
        out.append(r)
    return out


class TestListReportsCursor:
    async def test_orders_by_created_at_then_id(self):
        res = MagicMock()
        res.scalars.return_value.all.return_value = []
        session = _session(res)
        await ModerationRepository(session).list_reports(community_id=COMMUNITY_ID)
        assert "order by content_reports.created_at desc, content_reports.id desc" in _sql(session)

    async def test_next_cursor_encodes_last_row(self):
        rows = _reports(3)
        res = MagicMock()
        res.scalars.return_value.all.return_value = rows
        session = _session(res)
        items, cursor = await ModerationRepository(session).list_reports(limit=2)
        assert items == rows[:2]
        assert cursor is not None
        assert decode_report_cursor(cursor) == (rows[1].created_at, rows[1].id)

    async def test_cursor_applies_keyset_filter(self):
        res = MagicMock()
        res.scalars.return_value.all.return_value = []
        session = _session(res)
        cursor = encode_report_cursor(datetime.now(UTC), uuid.uuid4())
        await ModerationRepository(session).list_reports(cursor=cursor)
        sql = _sql(session)
        assert "content_reports.created_at <" in sql
        assert "content_reports.created_at =" in sql and "content_reports.id <" in sql

    async def test_invalid_cursor_ignored(self):
        assert decode_report_cursor("not-a-cursor") is None
