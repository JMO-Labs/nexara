"""
@file test_list_repos.py
@brief Unit tests for the list repositories (compiled SQL + signatures).
"""

from __future__ import annotations

import inspect
import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.dialects import postgresql

from app.models.list import List
from app.repositories.base import BaseRepository
from app.repositories.list_completion_repo import ListCompletionRepository
from app.repositories.list_item_repo import ListItemRepository
from app.repositories.list_keyset import decode_cursor, encode_cursor, parse_dt
from app.repositories.list_member_repo import ListMemberRepository
from app.repositories.list_repo import ListRepository
from app.repositories.list_signup_repo import ListSignupRepository
from app.repositories.list_template_repo import ListTemplateRepository

CID, UID, LID = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
ALL = [
    ListTemplateRepository,
    ListRepository,
    ListItemRepository,
    ListSignupRepository,
    ListCompletionRepository,
    ListMemberRepository,
]


def _session(rows: list[Any]) -> AsyncMock:
    s = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = rows
    result.scalar_one_or_none.return_value = rows[0] if rows else None
    s.execute = AsyncMock(return_value=result)
    return s


def _sql(session: AsyncMock) -> str:
    stmt = session.execute.call_args_list[-1].args[0]
    return str(stmt.compile(dialect=postgresql.dialect()))


@pytest.mark.parametrize("repo", ALL)
def test_extends_base(repo: type) -> None:
    assert issubclass(repo, BaseRepository) and repo.model is not None


def test_signatures() -> None:
    assert list(inspect.signature(ListRepository.list_visible).parameters) == [
        "self",
        "community_id",
        "viewer_id",
        "subgroup_ids",
        "member_list_ids",
        "cursor",
        "limit",
    ]
    assert "session" in inspect.signature(ListItemRepository.lock_item_for_update).parameters
    for name in ("sum_claimed", "create_claim", "delete_claim", "list_for_item"):
        assert hasattr(ListSignupRepository, name)
    for name in ("get_completion", "create_completion", "delete_completion"):
        assert hasattr(ListCompletionRepository, name)
    for name in ("get_member", "list_members", "add_member", "update_member", "remove_member"):
        assert hasattr(ListMemberRepository, name)


def test_cursor_roundtrip() -> None:
    now, rid = datetime.now(UTC), uuid.uuid4()
    assert decode_cursor(encode_cursor(now, rid), parse_dt) == (now, rid)
    assert decode_cursor("garbage!", parse_dt) is None
    assert decode_cursor(None, int) is None


async def test_list_visible_or_clause_soft_delete_and_block() -> None:
    s = _session([])
    await ListRepository(s).list_visible(CID, UID, [uuid.uuid4()], [LID])
    sql = _sql(s)
    assert "list.deleted_at IS NULL" in sql
    assert sql.count("list.visibility =") == 4
    assert " OR " in sql and "user_blocks" in sql


async def test_list_visible_pagination_cursor() -> None:
    rows = []
    for _ in range(3):
        r = MagicMock(spec=List)
        r.id, r.created_at = uuid.uuid4(), datetime.now(UTC)
        rows.append(r)
    s = _session(rows)
    page, nxt = await ListRepository(s).list_visible(CID, UID, [], [], limit=2)
    assert len(page) == 2 and nxt is not None
    await ListRepository(s).list_visible(CID, UID, [], [], cursor=nxt)
    assert "(list.created_at, list.id) <" in _sql(s)


async def test_lock_item_for_update() -> None:
    s = _session([])
    await ListItemRepository(AsyncMock()).lock_item_for_update(uuid.uuid4(), s)
    sql = _sql(s)
    assert "FOR UPDATE" in sql and "list_item.deleted_at IS NULL" in sql


async def test_items_keyset_and_bad_sort() -> None:
    s = _session([])
    await ListItemRepository(s).list_items_keyset(LID, cursor=encode_cursor(3, LID))
    sql = _sql(s)
    assert "(list_item.position, list_item.id) >" in sql and "deleted_at IS NULL" in sql
    with pytest.raises(ValueError):
        await ListItemRepository(s).list_items_keyset(LID, sort_by="nope")


async def test_template_visibility_and_block() -> None:
    s = _session([])
    await ListTemplateRepository(s).list_for_community(CID, UID)
    sql = _sql(s)
    assert "is_shared" in sql and "author_id" in sql and "deleted_at IS NULL" in sql
    assert "user_blocks" in sql
    assert "author_id IS NULL OR" in sql


async def test_increment_counters_validates() -> None:
    s = _session([])
    repo = ListRepository(s)
    await repo.increment_counters(LID, {"item_count": 1})
    assert "UPDATE list SET item_count=" in _sql(s)
    with pytest.raises(ValueError):
        await repo.increment_counters(LID, {"title": 1})


async def test_sum_claimed() -> None:
    s = AsyncMock()
    res = MagicMock()
    res.scalar_one.return_value = 4
    s.execute = AsyncMock(return_value=res)
    assert await ListSignupRepository(s).sum_claimed(LID) == 4


async def test_template_get_by_id_eager_loads_children() -> None:
    """@brief Async sessions cannot lazy-load; clone needs fields+items loaded."""
    s = _session([MagicMock()])
    await ListTemplateRepository(s).get_by_id(LID, CID)
    stmt = s.execute.call_args_list[-1].args[0]
    paths = " ".join(str(opt.path) for opt in stmt._with_options)
    assert "ListTemplate.fields" in paths and "ListTemplate.items" in paths
    sql = _sql(s)
    assert "list_template.community_id" in sql and "deleted_at IS NULL" in sql
