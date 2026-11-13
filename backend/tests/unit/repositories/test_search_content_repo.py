"""
@file test_search_content_repo.py
@brief Mock-session unit tests: subgroup/comment search, FTS helpers, member roles.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.subgroup import Subgroup
from app.repositories.search_fts import _fts_expressions
from app.repositories.search_repo import SearchRepository
from app.repositories.subgroup_member_repo import SubgroupMemberRepository

CID = uuid.UUID("00000000-0000-0000-0000-000000000001")
VIEWER = uuid.uuid4()


def _session(rows: list[tuple[object, float]], total: int = 0) -> AsyncMock:
    session = AsyncMock()
    page = MagicMock()
    page.all.return_value = rows
    count = MagicMock()
    count.scalar_one.return_value = total
    session.execute.side_effect = [page, count]
    return session


@pytest.mark.parametrize("method", ["search_subgroups", "search_comments"])
@pytest.mark.parametrize("query", ["", "   "])
async def test_blank_query_short_circuits(method, query) -> None:
    session = _session([])
    result = await getattr(SearchRepository(session), method)(query, "", CID, VIEWER, None, 10)
    assert result == ([], None, 0)
    session.execute.assert_not_awaited()


@pytest.mark.parametrize("method", ["search_subgroups", "search_comments"])
async def test_bad_cursor_falls_back_to_offset_zero(method) -> None:
    session = _session([])
    await getattr(SearchRepository(session), method)("hi", "hi:*", CID, VIEWER, "garbage", 10)
    page_stmt = session.execute.await_args_list[0].args[0]
    assert page_stmt._offset_clause.value == 0


@pytest.mark.parametrize("method", ["search_subgroups", "search_comments"])
async def test_pagination_trims_and_sets_next_cursor(method) -> None:
    rows = [(MagicMock(), 0.5), (MagicMock(), 0.4), (MagicMock(), 0.3)]
    session = _session(rows, total=7)
    items, nxt, total = await getattr(SearchRepository(session), method)(
        "hi", "hi:*", CID, VIEWER, "10", 2
    )
    assert len(items) == 2
    assert items[0] == (rows[0][0], 0.5)
    assert nxt == "12"
    assert total == 7


@pytest.mark.parametrize("method", ["search_subgroups", "search_comments"])
async def test_last_page_has_no_next_cursor(method) -> None:
    session = _session([(MagicMock(), 0.5)], total=1)
    items, nxt, total = await getattr(SearchRepository(session), method)(
        "hi", "", CID, VIEWER, None, 5
    )
    assert len(items) == 1
    assert nxt is None
    assert total == 1


async def test_subgroup_search_excludes_archived_and_scopes_visibility() -> None:
    session = _session([])
    await SearchRepository(session).search_subgroups("hi", "hi:*", CID, VIEWER, None, 5)
    sql = str(session.execute.await_args_list[0].args[0]).lower()
    assert "archived_at is null" in sql
    assert "is_private" in sql
    assert "visible_subgroups" in sql


def test_fts_expressions_without_prefix() -> None:
    match, rank, extra = _fts_expressions(Subgroup.search_fts, "")
    assert extra == {}
    assert "greatest" not in str(rank).lower()
    assert "q_prefix" not in str(match)


def test_fts_expressions_with_prefix() -> None:
    match, rank, extra = _fts_expressions(Subgroup.search_fts, "app:*")
    assert extra == {"q_prefix": "app:*"}
    assert "greatest" in str(rank).lower()
    assert "q_prefix" in str(match)


async def test_list_my_roles_maps_subgroup_to_role() -> None:
    a, b = uuid.uuid4(), uuid.uuid4()
    session = AsyncMock()
    result = MagicMock()
    result.all.return_value = [(a, "admin"), (b, "member")]
    session.execute.return_value = result
    roles = await SubgroupMemberRepository(session).list_my_roles(VIEWER)
    assert roles == {a: "admin", b: "member"}
