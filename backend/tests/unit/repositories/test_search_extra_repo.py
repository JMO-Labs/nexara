"""
@file test_search_extra_repo.py
@brief Unit tests for GalleryPollSearchMixin (mock session, no DB).
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.repositories.search_extra_repo import _offset
from app.repositories.search_repo import SearchRepository

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
VIEWER_ID = uuid.uuid4()


def _repo(rows: list, total: int) -> tuple[SearchRepository, AsyncMock]:
    """@brief Build a repo whose session returns *rows* then *total*."""
    session = AsyncMock()
    page = MagicMock()
    page.all.return_value = rows
    count = MagicMock()
    count.scalar_one.return_value = total
    session.execute = AsyncMock(side_effect=[page, count])
    return SearchRepository(session), session


class TestOffset:
    """@brief Tests for _offset()."""

    def test_none_is_zero(self):
        assert _offset(None) == 0

    def test_valid(self):
        assert _offset("20") == 20

    def test_invalid_is_zero(self):
        assert _offset("abc") == 0


@pytest.mark.parametrize("method", ["search_galleries", "search_polls"])
class TestSearchCommon:
    """@brief Behaviour shared by gallery and poll search."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("query", ["", "   "])
    async def test_blank_query_short_circuits(self, method: str, query: str):
        repo, session = _repo([], 0)
        result = await getattr(repo, method)(query, "", COMMUNITY_ID, VIEWER_ID, None, 10)
        assert result == ([], None, 0)
        session.execute.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("prefix", ["", "pic:*"])
    async def test_no_next_cursor_when_page_not_full(self, method: str, prefix: str):
        repo, session = _repo([], 0)
        items, cursor, total = await getattr(repo, method)(
            "pic", prefix, COMMUNITY_ID, VIEWER_ID, "bad", 10
        )
        assert (items, cursor, total) == ([], None, 0)
        params = session.execute.call_args_list[0].args[1]
        assert params["q"] == "pic"
        assert ("q_prefix" in params) == bool(prefix)

    @pytest.mark.asyncio
    async def test_next_cursor_when_more_rows(self, method: str):
        rows = [(MagicMock(), MagicMock(), 0.5)] * 3
        repo, _ = _repo(rows, 7)
        items, cursor, total = await getattr(repo, method)(
            "pic", "", COMMUNITY_ID, VIEWER_ID, "4", 2
        )
        assert len(items) == 2
        assert cursor == "6"
        assert total == 7
