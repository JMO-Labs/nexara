"""
@file test_admin_storage_service.py
@brief Unit tests for AdminStorageService.
"""

from __future__ import annotations

import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.repositories.storage_repo import StorageRepository
from app.services.admin_storage_service import AdminStorageService

CID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _snap(d: date, total: int) -> MagicMock:
    s = MagicMock()
    s.snapshot_date = d
    s.total_bytes = total
    s.media_images_bytes = 600
    s.media_videos_bytes = 300
    s.media_thumbnails_bytes = 10
    s.media_other_bytes = None
    s.db_estimated_bytes = 90
    s.total_media_files = 5
    s.total_posts = 7
    return s


def _user(name: str, used: int) -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.display_name = name
    u.username = name.lower()
    u.storage_used = used
    return u


@pytest.fixture
def repo() -> AsyncMock:
    return AsyncMock(spec=StorageRepository)


class TestOverview:
    @pytest.mark.asyncio
    async def test_current_and_snapshots(self, repo):
        snaps = [_snap(date(2026, 1, 1), 900), _snap(date(2026, 1, 2), 1000)]
        repo.snapshots_since.return_value = snaps
        repo.top_users.return_value = [_user("Ann", 500)]
        repo.total_user_bytes.return_value = 1000
        svc = AdminStorageService(repo, CID)
        res = await svc.get_overview(days=30)
        assert res.current.total_bytes == 1000
        assert res.current.by_category["images"] == 600
        assert res.current.by_category["other"] == 0
        assert len(res.snapshots) == 2
        assert res.per_user[0].display_name == "Ann"

    @pytest.mark.asyncio
    async def test_empty_snapshots(self, repo):
        repo.snapshots_since.return_value = []
        repo.top_users.return_value = []
        repo.total_user_bytes.return_value = 0
        res = await AdminStorageService(repo, CID).get_overview()
        assert res.current.total_bytes == 0
        assert res.snapshots == []


class TestUsers:
    @pytest.mark.asyncio
    async def test_percent_of_total_and_paging(self, repo):
        repo.user_page.return_value = ([_user("Bob", 250)], 120)
        repo.total_user_bytes.return_value = 1000
        res = await AdminStorageService(repo, CID).list_users(page=2, page_size=100)
        assert res.total == 120
        assert res.items[0].used_bytes == 250
        assert res.items[0].percent_of_total == 25.0
        repo.user_page.assert_awaited_once_with(CID, offset=100, limit=100)

    @pytest.mark.asyncio
    async def test_zero_total_no_division_error(self, repo):
        repo.user_page.return_value = ([_user("Bob", 0)], 1)
        repo.total_user_bytes.return_value = 0
        res = await AdminStorageService(repo, CID).list_users()
        assert res.items[0].percent_of_total == 0.0
