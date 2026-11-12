"""
@file test_search_extra_repo.py
@brief Unit tests (mocked session) for gallery/poll search mixin.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.repositories.search_extra_repo import _offset
from app.repositories.search_repo import SearchRepository

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
VIEWER_ID = uuid.uuid4()


def _repo(rows: list, total: int = 0) -> tuple[SearchRepository, AsyncMock]:
    """@brief Build a repo whose session returns *rows* then *total*."""
    session = AsyncMock()
    page = MagicMock()
    page.all.return_value = rows
    count = MagicMock()
    count.scalar_one.return_value = total
    session.execute = AsyncMock(side_effect=[page, count])
    return SearchRepository(session), session


class TestOffset:
    """@brief Cursor parsing."""

    @pytest.mark.parametrize(("cursor", "expected"), [(None, 0), ("", 0), ("20", 20), ("abc", 0)])
    def test_offset(self, cursor: str | None, expected: int) -> None:
        assert _offset(cursor) == expected


@pytest.mark.parametrize("method", ["search_galleries", "search_polls"])
@pytest.mark.parametrize("query", ["", "   "])
async def test_blank_query_short_circuits(method: str, query: str) -> None:
    repo, session = _repo([])
    result = await getattr(repo, method)(query, "", COMMUNITY_ID, VIEWER_ID, None, 10)
    assert result == ([], None, 0)
    session.execute.assert_not_called()


class TestSearchGalleries:
    """@brief search_galleries."""

    async def test_returns_items_with_rank(self) -> None:
        g = MagicMock()
        repo, session = _repo([(g, 0.5)], total=1)
        items, nxt, total = await repo.search_galleries(
            "trip", "", COMMUNITY_ID, VIEWER_ID, None, 10
        )
        assert items == [(g, 0.5)]
        assert (nxt, total) == (None, 1)
        assert session.execute.await_count == 2

    async def test_prefix_query_adds_param(self) -> None:
        repo, session = _repo([], total=0)
        await repo.search_galleries("tr", "tr:*", COMMUNITY_ID, VIEWER_ID, None, 10)
        assert session.execute.await_args_list[0].args[1]["q_prefix"] == "tr:*"

    async def test_next_cursor_when_more_rows(self) -> None:
        rows = [(MagicMock(), 0.1) for _ in range(3)]
        repo, _ = _repo(rows, total=3)
        items, nxt, _total = await repo.search_galleries(
            "trip", "", COMMUNITY_ID, VIEWER_ID, "5", 2
        )
        assert len(items) == 2
        assert nxt == "7"


class TestSearchPolls:
    """@brief search_polls."""

    async def test_returns_poll_post_rank(self) -> None:
        poll, post = MagicMock(), MagicMock()
        repo, session = _repo([(poll, post, 0.9)], total=1)
        items, nxt, total = await repo.search_polls(
            "lunch", "lun:*", COMMUNITY_ID, VIEWER_ID, None, 10
        )
        assert items == [(poll, post, 0.9)]
        assert (nxt, total) == (None, 1)
        assert session.execute.await_args_list[0].args[1] == {"q": "lunch", "q_prefix": "lun:*"}

    async def test_next_cursor_when_more_rows(self) -> None:
        rows = [(MagicMock(), MagicMock(), 0.1) for _ in range(2)]
        repo, _ = _repo(rows, total=2)
        items, nxt, _total = await repo.search_polls("lunch", "", COMMUNITY_ID, VIEWER_ID, None, 1)
        assert len(items) == 1
        assert nxt == "1"
