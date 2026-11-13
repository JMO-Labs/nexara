"""
@file test_export_download.py
@brief Route-level tests for the data-export download endpoint.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1 import export
from app.core.dependencies import get_current_user
from app.models.user_export import UserExport
from app.repositories.user_export_repo import UserExportRepository

NOW = datetime.now(UTC)
ZIP = b"PK\x03\x04fake-zip-bytes"


def _export(user_id, **kw) -> MagicMock:
    row = MagicMock(spec=UserExport)
    row.id = uuid.uuid4()
    row.user_id = user_id
    row.status = kw.get("status", "ready")
    row.file_key = "exports/x.zip"
    row.expires_at = kw.get("expires_at", NOW + timedelta(hours=24))
    return row


@pytest.fixture
def user():
    u = MagicMock()
    u.id = uuid.uuid4()
    u.community_id = uuid.uuid4()
    return u


@pytest.fixture
def repo() -> AsyncMock:
    return AsyncMock(spec=UserExportRepository)


@pytest.fixture
def storage() -> AsyncMock:
    s = AsyncMock()
    s.get.return_value = ZIP
    return s


@pytest.fixture
def client(test_app, user, repo, storage):
    test_app.dependency_overrides[get_current_user] = lambda: user
    test_app.dependency_overrides[export._get_repo] = lambda: repo
    test_app.dependency_overrides[export._get_storage] = lambda: storage
    yield AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test")
    test_app.dependency_overrides.clear()


async def _get(client, row):
    async with client as c:
        return await c.get(f"/api/v1/export/{row.id}/download")


class TestDownload:
    async def test_streams_zip_with_disposition(self, client, repo, storage, user):
        row = _export(user.id)
        repo.get_by_id.return_value = row
        resp = await _get(client, row)
        assert resp.status_code == 200
        assert resp.content == ZIP
        assert resp.headers["content-type"] == "application/zip"
        assert resp.headers["content-disposition"] == (
            f'attachment; filename="nexara-export-{row.id}.zip"'
        )
        storage.get.assert_awaited_once_with("exports/x.zip")
        repo.mark_downloaded.assert_awaited_once()

    async def test_expired_returns_410(self, client, repo, user):
        row = _export(user.id, expires_at=NOW - timedelta(seconds=1))
        repo.get_by_id.return_value = row
        resp = await _get(client, row)
        assert resp.status_code == 410
        assert resp.json()["error"]["message"] == "Download link has expired"

    async def test_wrong_user_returns_403(self, client, repo):
        row = _export(uuid.uuid4())
        repo.get_by_id.return_value = row
        assert (await _get(client, row)).status_code == 403

    async def test_missing_returns_404(self, client, repo):
        repo.get_by_id.return_value = None
        assert (await _get(client, _export(uuid.uuid4()))).status_code == 404

    @pytest.mark.parametrize("status", ["pending", "processing"])
    async def test_not_ready_returns_400(self, client, repo, user, status):
        row = _export(user.id, status=status)
        repo.get_by_id.return_value = row
        assert (await _get(client, row)).status_code == 400

    @pytest.mark.parametrize("status", ["expired", "failed"])
    async def test_expired_or_failed_status_returns_410(self, client, repo, user, status):
        row = _export(user.id, status=status)
        repo.get_by_id.return_value = row
        assert (await _get(client, row)).status_code == 410

    async def test_storage_error_returns_500(self, client, repo, storage, user):
        row = _export(user.id)
        repo.get_by_id.return_value = row
        storage.get.side_effect = RuntimeError("boom")
        async with client as c:
            resp = await c.get(f"/api/v1/export/{row.id}/download")
        assert resp.status_code == 500
        repo.mark_downloaded.assert_not_awaited()
