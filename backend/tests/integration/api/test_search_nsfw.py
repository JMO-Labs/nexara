"""
@file test_search_nsfw.py
@brief NSFW filtering in search: hidden for non-adults, shown (flagged) for adults.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.dialects import postgresql

from app.repositories.search_repo import SearchRepository, is_adult
from app.services.search_service import SearchService

CID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _post(nsfw: bool) -> MagicMock:
    p = MagicMock()
    p.id = uuid.uuid4()
    p.content = "hello world"
    p.created_at = datetime.now(UTC)
    p.is_nsfw = nsfw
    return p


def _service(adult: bool, rows):
    repo = AsyncMock(spec=SearchRepository)
    repo.viewer_is_adult.return_value = adult
    repo.search_posts.return_value = (rows, None, len(rows))
    return SearchService(repo, CID), repo


async def _search(svc):
    user = MagicMock()
    user.id = uuid.uuid4()
    return await svc.search("hello", user, ["posts"], None, 20)


class TestIsAdult:
    def test_adult_needs_age_and_flag(self):
        old = date.today() - timedelta(days=365 * 30)
        young = date.today() - timedelta(days=365 * 10)
        assert is_adult(old, True)
        assert not is_adult(old, False)
        assert not is_adult(young, True)
        assert not is_adult(None, True)


class TestSearchNsfw:
    async def test_non_adult_excludes_nsfw_in_repo_call(self):
        svc, repo = _service(False, [])
        await _search(svc)
        assert repo.search_posts.call_args.kwargs["include_nsfw"] is False

    async def test_adult_includes_nsfw_and_flags_item(self):
        svc, repo = _service(True, [(_post(True), 1.0), (_post(False), 0.5)])
        res = await _search(svc)
        assert repo.search_posts.call_args.kwargs["include_nsfw"] is True
        items = res.results["posts"].items
        assert [i.is_nsfw for i in items] == [True, False]
        assert not any(i.blur for i in items)

    async def test_non_adult_nsfw_row_is_blurred_defensively(self):
        svc, _ = _service(False, [(_post(True), 1.0)])
        item = (await _search(svc)).results["posts"].items[0]
        assert item.is_nsfw and item.blur


class TestRepoSql:
    @pytest.mark.parametrize("include,expected", [(False, True), (True, False)])
    async def test_where_clause(self, include, expected):
        session = AsyncMock()
        result = MagicMock()
        result.all.return_value = []
        result.scalar_one.return_value = 0
        session.execute.return_value = result
        repo = SearchRepository(session)
        await repo.search_posts("hello", "", CID, uuid.uuid4(), None, 10, include_nsfw=include)
        sql = str(session.execute.call_args_list[0].args[0].compile(dialect=postgresql.dialect()))
        where = sql.split("WHERE", 1)[1]
        assert ("posts.is_nsfw" in where) is expected
