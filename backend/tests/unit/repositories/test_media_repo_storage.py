"""
@file test_media_repo_storage.py
@brief Unit tests for MediaRepository.get_user_storage_by_type.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.dialects import postgresql

from app.repositories.media_repo import MediaRepository

USER_ID = uuid.uuid4()
COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _repo(rows: list[tuple[str, int]]) -> tuple[MediaRepository, AsyncMock]:
    session = AsyncMock()
    result = MagicMock()
    result.all.return_value = rows
    session.execute = AsyncMock(return_value=result)
    return MediaRepository(session), session


class TestStorageByType:
    """@brief Tests for per-category storage sums."""

    @pytest.mark.asyncio
    async def test_empty_returns_all_zero_keys(self):
        repo, _ = _repo([])
        out = await repo.get_user_storage_by_type(USER_ID, COMMUNITY_ID)
        assert out == {"photos": 0, "videos": 0, "documents": 0, "other": 0}

    @pytest.mark.asyncio
    async def test_maps_rows_to_ints(self):
        repo, _ = _repo([("photos", 10), ("documents", 5)])
        out = await repo.get_user_storage_by_type(USER_ID, COMMUNITY_ID)
        assert out == {"photos": 10, "videos": 0, "documents": 5, "other": 0}

    @pytest.mark.asyncio
    async def test_category_patterns_and_filters(self):
        repo, session = _repo([])
        await repo.get_user_storage_by_type(USER_ID, COMMUNITY_ID)
        stmt = session.execute.await_args.args[0]
        sql = str(
            stmt.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True})
        )
        flat = " ".join(sql.split()).replace("%%", "%")
        assert "media.content_type LIKE 'image/%') THEN 'photos'" in flat
        assert "media.content_type LIKE 'video/%') THEN 'videos'" in flat
        assert "'application/pdf'" in flat
        assert "'application/msword'" in flat
        assert "media.content_type LIKE 'text/%'" in flat
        assert "media.content_type LIKE 'application/vnd.%')" in flat
        assert "THEN 'documents'" in flat
        assert "ELSE 'other'" in flat
        assert "GROUP BY" in flat
        where = flat.split("WHERE")[1].split("GROUP BY")[0]
        assert f"media.uploader_id = '{USER_ID}'" in where
        assert f"media.community_id = '{COMMUNITY_ID}'" in where
