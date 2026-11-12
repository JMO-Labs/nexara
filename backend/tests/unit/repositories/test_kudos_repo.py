"""
@file test_kudos_repo.py
@brief Unit tests for KudosRepository create and list query building (nexara#269).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.dialects import postgresql

from app.core.exceptions import AppError
from app.models.post import Post
from app.repositories.kudos_repo import KudosRepository

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
VIEWER = uuid.uuid4()


def _rows(n: int) -> list[tuple[MagicMock, MagicMock]]:
    """@brief n (post, recipient) rows with descending created_at."""
    now = datetime.now(UTC)
    out = []
    for i in range(n):
        p = MagicMock(spec=Post)
        p.created_at = now - timedelta(minutes=i)
        out.append((p, MagicMock()))
    return out


def _session(rows: list) -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    result = MagicMock()
    result.all.return_value = rows
    session.execute = AsyncMock(return_value=result)
    return session


def _sql(session: AsyncMock) -> str:
    stmt = session.execute.await_args.args[0]
    return str(stmt.compile(dialect=postgresql.dialect()))


class TestCreateKudos:
    async def test_community_visibility_without_subgroup(self) -> None:
        repo = KudosRepository(_session([]))
        repo.create = AsyncMock(side_effect=lambda p: p)  # type: ignore[method-assign]
        rid = uuid.uuid4()
        post = await repo.create_kudos(VIEWER, rid, "hi", COMMUNITY_ID)
        assert (post.recipient_id, post.content, post.visibility) == (rid, "hi", "community")

    async def test_subgroup_visibility_with_subgroup(self) -> None:
        repo = KudosRepository(_session([]))
        repo.create = AsyncMock(side_effect=lambda p: p)  # type: ignore[method-assign]
        sg = uuid.uuid4()
        post = await repo.create_kudos(VIEWER, uuid.uuid4(), "hi", COMMUNITY_ID, sg)
        assert (post.subgroup_id, post.visibility) == (sg, "subgroup")


class TestListKudos:
    async def test_filters_and_no_next_cursor(self) -> None:
        rows = _rows(2)
        session = _session(rows)
        out, cursor = await KudosRepository(session).list_kudos(COMMUNITY_ID, VIEWER, limit=5)
        assert out == rows and cursor is None
        sql = _sql(session)
        assert "posts.recipient_id IS NOT NULL" in sql
        assert "posts.deleted_at IS NULL" in sql
        assert "subgroup_members" in sql
        assert "user_blocks" in sql
        assert "ORDER BY posts.created_at DESC" in sql

    async def test_recipient_and_cursor_filters(self) -> None:
        session = _session([])
        before = datetime.now(UTC).isoformat()
        await KudosRepository(session).list_kudos(
            COMMUNITY_ID, VIEWER, recipient_id=uuid.uuid4(), cursor=before
        )
        sql = _sql(session)
        assert "posts.recipient_id = " in sql
        assert "posts.created_at < " in sql

    async def test_overflow_trims_and_sets_cursor(self) -> None:
        rows = _rows(3)
        out, cursor = await KudosRepository(_session(rows)).list_kudos(
            COMMUNITY_ID, VIEWER, limit=2
        )
        assert len(out) == 2
        assert cursor == rows[1][0].created_at.isoformat()

    async def test_invalid_cursor_raises(self) -> None:
        with pytest.raises(AppError) as exc:
            await KudosRepository(_session([])).list_kudos(COMMUNITY_ID, VIEWER, cursor="bad")
        assert exc.value.code == "INVALID_CURSOR"
