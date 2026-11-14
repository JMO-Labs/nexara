"""
@file test_base_repo_list_count.py
@brief Unit tests for BaseRepository.list() scoping/cursor and count() filters.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

from app.models.user import User
from app.repositories.base import BaseRepository


class _Repo(BaseRepository[User]):
    model = User


def _session(rows=None, scalar=0):
    result = MagicMock()
    result.scalars.return_value.all.return_value = rows or []
    result.scalar_one.return_value = scalar
    session = MagicMock()
    session.execute = AsyncMock(return_value=result)
    return session


def _sql(session) -> str:
    stmt = session.execute.call_args.args[0]
    return str(stmt.compile(compile_kwargs={"literal_binds": True}))


class TestListScoping:
    async def test_scopes_by_community_and_default_order(self):
        cid = uuid.uuid4()
        s = _session()
        await _Repo(s).list(community_id=cid)
        sql = _sql(s)
        assert str(cid).replace("-", "") in sql.replace("-", "")
        assert "ORDER BY" in sql and "created_at DESC" in sql

    async def test_explicit_order_by_used(self):
        s = _session()
        await _Repo(s).list(order_by=User.id.asc())
        sql = _sql(s)
        assert "ORDER BY" in sql and "created_at DESC" not in sql

    async def test_invalid_cursor_ignored(self):
        s = _session()
        rows, nxt = await _Repo(s).list(cursor="not-a-uuid")
        assert rows == [] and nxt is None
        assert "users.id <" not in _sql(s)

    async def test_valid_cursor_filters_and_next_cursor(self):
        cur = uuid.uuid4()
        items = [MagicMock(id=uuid.uuid4()) for _ in range(3)]
        s = _session(rows=items)
        rows, nxt = await _Repo(s).list(limit=2, cursor=str(cur))
        assert "users.id <" in _sql(s)
        assert rows == items[:2]
        assert nxt == str(items[1].id)


class TestCount:
    async def test_count_filters_deleted_and_community(self):
        cid = uuid.uuid4()
        s = _session(scalar=7)
        assert await _Repo(s).count(community_id=cid) == 7
        sql = _sql(s)
        assert "deleted_at IS NULL" in sql
        assert "community_id" in sql
