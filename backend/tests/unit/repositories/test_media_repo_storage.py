"""
@file test_media_repo_storage.py
@brief Unit tests for MediaRepository.get_user_storage_by_type.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

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
    async def test_single_grouped_query_with_filters(self):
        repo, session = _repo([])
        await repo.get_user_storage_by_type(USER_ID, COMMUNITY_ID)
        session.execute.assert_awaited_once()
        sql = str(session.execute.await_args.args[0]).upper()
        assert "GROUP BY" in sql
        assert "CASE" in sql
        assert "UPLOADER_ID" in sql
        assert "COMMUNITY_ID" in sql
