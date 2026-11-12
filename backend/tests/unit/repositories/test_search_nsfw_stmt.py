"""
@file test_search_nsfw_stmt.py
@brief Mock-session unit tests: NSFW predicates in search repository statements.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.repositories.search_repo import SearchRepository

CID = uuid.UUID("00000000-0000-0000-0000-000000000001")
VIEWER = uuid.uuid4()


def _session() -> AsyncMock:
    session = AsyncMock()
    rows = MagicMock()
    rows.all.return_value = []
    count = MagicMock()
    count.scalar_one.return_value = 0
    session.execute.side_effect = [rows, count]
    return session


def _sql(session: AsyncMock) -> list[str]:
    return [str(c.args[0]).lower() for c in session.execute.await_args_list]


@pytest.mark.parametrize("method", ["search_posts", "search_comments", "search_polls"])
@pytest.mark.parametrize("include", [False, True])
async def test_nsfw_filter_applied_only_for_non_adults(method, include) -> None:
    session = _session()
    repo = SearchRepository(session)
    await getattr(repo, method)("hello", "hello:*", CID, VIEWER, None, 20, include_nsfw=include)
    # both the page query and the count query must carry (or omit) the filter
    for sql in _sql(session):
        assert ("posts.is_nsfw" in sql and "false" in sql) is (not include)
