"""
@file test_search_extra_repo.py
@brief Unit tests (mocked session) for gallery/poll search mixin.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.repositories.search_extra_repo import GalleryPollSearchMixin, _offset

CID, VID = uuid.uuid4(), uuid.uuid4()


class _Repo(GalleryPollSearchMixin):
    """@brief Concrete host for the mixin."""

    def __init__(self, session: AsyncMock) -> None:
        self._session = session


def _session(rows: list, total: int) -> AsyncMock:
    """@brief Session returning *rows* for the page query and *total* for count."""
    page = MagicMock()
    page.all.return_value = rows
    count = MagicMock()
    count.scalar_one.return_value = total
    s = AsyncMock()
    s.execute = AsyncMock(side_effect=[page, count])
    return s


class TestOffset:
    """@brief _offset cursor parsing."""

    def test_none_and_empty(self):
        assert _offset(None) == 0
        assert _offset("") == 0

    def test_valid(self):
        assert _offset("20") == 20

    def test_invalid(self):
        assert _offset("abc") == 0


class TestSearchGalleries:
    """@brief search_galleries."""

    @pytest.mark.parametrize("q", ["", "   "])
    async def test_blank_query_short_circuits(self, q):
        s = AsyncMock()
        assert await _Repo(s).search_galleries(q, "", CID, VID, None, 10) == ([], None, 0)
        s.execute.assert_not_called()

    @pytest.mark.parametrize("prefix", ["", "foo:*"])
    async def test_returns_items_without_next_cursor(self, prefix):
        s = _session([("g1", 0.5)], 1)
        items, nxt, total = await _Repo(s).search_galleries("foo", prefix, CID, VID, None, 10)
        assert items == [("g1", 0.5)]
        assert nxt is None
        assert total == 1

    async def test_next_cursor_and_truncation(self):
        s = _session([("a", 1.0), ("b", 0.9), ("c", 0.8)], 3)
        items, nxt, total = await _Repo(s).search_galleries("foo", "foo:*", CID, VID, "5", 2)
        assert [i[0] for i in items] == ["a", "b"]
        assert nxt == "7"
        assert total == 3
        assert s.execute.await_count == 2


class TestSearchPolls:
    """@brief search_polls."""

    async def test_blank_query_short_circuits(self):
        s = AsyncMock()
        assert await _Repo(s).search_polls(" ", "", CID, VID, None, 10) == ([], None, 0)
        s.execute.assert_not_called()

    @pytest.mark.parametrize("prefix", ["", "foo:*"])
    async def test_returns_triples(self, prefix):
        s = _session([("poll", "post", 0.4)], 1)
        items, nxt, total = await _Repo(s).search_polls("foo", prefix, CID, VID, "bad", 10)
        assert items == [("poll", "post", 0.4)]
        assert nxt is None
        assert total == 1

    async def test_next_cursor(self):
        s = _session([("p1", "q1", 1.0), ("p2", "q2", 0.9)], 2)
        items, nxt, _ = await _Repo(s).search_polls("foo", "", CID, VID, None, 1)
        assert len(items) == 1
        assert nxt == "1"
