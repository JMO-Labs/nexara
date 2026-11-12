"""
@file test_bookmark_repo.py
@brief Unit tests for BookmarkRepository.list_for_user (filters, order, paging).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.dialects import postgresql

from app.core.exceptions import AppError
from app.models.bookmark import Bookmark
from app.repositories import bookmark_repo
from app.repositories.bookmark_repo import BookmarkRepository

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
USER_ID = uuid.uuid4()


def _bookmarks(n: int) -> list[Bookmark]:
    """@brief Build n mock bookmarks with descending created_at."""
    now = datetime.now(UTC)
    out = []
    for i in range(n):
        b = MagicMock(spec=Bookmark)
        b.id, b.post_id = uuid.uuid4(), uuid.uuid4()
        b.created_at = now - timedelta(minutes=i)
        out.append(b)
    return out


def _session(rows: list[Bookmark]) -> AsyncMock:
    """@brief Mock session whose execute returns the given bookmark rows."""
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = rows
    session.execute = AsyncMock(return_value=result)
    return session


@pytest.fixture(autouse=True)
def _fake_enrich(monkeypatch: pytest.MonkeyPatch) -> None:
    """@brief Replace post enrichment with a trivial id map."""

    async def fake(_s: Any, ids: list[uuid.UUID], _v: Any) -> dict[uuid.UUID, dict[str, Any]]:
        return {i: {"id": str(i)} for i in ids}

    monkeypatch.setattr(bookmark_repo, "enrich_posts", fake)


def _sql(session: AsyncMock) -> str:
    """@brief Compile the captured list statement to SQL text."""
    stmt = session.execute.await_args_list[0].args[0]
    return str(stmt.compile(dialect=postgresql.dialect()))


class TestListForUser:
    """@brief AC3/AC4: own bookmarks only, newest first, soft-deleted posts excluded."""

    async def test_filters_user_community_and_soft_deleted(self) -> None:
        session = _session([])
        await BookmarkRepository(session).list_for_user(USER_ID, COMMUNITY_ID)
        sql = _sql(session)
        assert "bookmarks.user_id = " in sql
        assert "bookmarks.community_id = " in sql
        assert "posts.deleted_at IS NULL" in sql

    async def test_orders_newest_first(self) -> None:
        session = _session([])
        await BookmarkRepository(session).list_for_user(USER_ID, COMMUNITY_ID)
        assert "ORDER BY bookmarks.created_at DESC" in _sql(session)

    async def test_applies_cursor(self) -> None:
        session = _session([])
        cursor = datetime.now(UTC).isoformat()
        await BookmarkRepository(session).list_for_user(USER_ID, COMMUNITY_ID, cursor=cursor)
        assert "bookmarks.created_at < " in _sql(session)

    async def test_invalid_cursor_raises(self) -> None:
        session = _session([])
        with pytest.raises(AppError) as exc:
            await BookmarkRepository(session).list_for_user(
                USER_ID, COMMUNITY_ID, cursor="2026-01-01T00:00:00 00:00x"
            )
        assert exc.value.code == "INVALID_CURSOR"
        assert exc.value.status_code == 400

    async def test_extra_row_yields_next_cursor(self) -> None:
        rows = _bookmarks(3)
        session = _session(rows)
        items, next_cursor = await BookmarkRepository(session).list_for_user(
            USER_ID, COMMUNITY_ID, limit=2
        )
        assert len(items) == 2
        assert next_cursor == rows[1].created_at.isoformat()

    async def test_exact_limit_has_no_next_cursor(self) -> None:
        session = _session(_bookmarks(2))
        items, next_cursor = await BookmarkRepository(session).list_for_user(
            USER_ID, COMMUNITY_ID, limit=2
        )
        assert len(items) == 2
        assert next_cursor is None
