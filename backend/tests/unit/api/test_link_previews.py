"""
@file test_link_previews.py
@brief Unit tests for /api/v1/link-previews endpoints (mocked repo/service).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.dependencies import get_current_user
from app.models.link_preview import LinkPreview
from app.repositories.link_preview_repo import LinkPreviewRepository


def _preview(image_url: str | None = "https://cdn.example.com/a.png") -> MagicMock:
    p = MagicMock(spec=LinkPreview)
    p.id = uuid.uuid4()
    p.url = "https://example.com/x"
    p.title = "Title"
    p.description = "Desc"
    p.image_url = image_url
    p.site_name = "Example"
    p.provider_type = None
    p.provider_id = None
    p.fetched_at = datetime.now(UTC)
    p.expires_at = datetime.now(UTC) + timedelta(days=7)
    return p


def _repo(preview: MagicMock | None) -> AsyncMock:
    repo = AsyncMock(spec=LinkPreviewRepository)
    repo.get_by_id.return_value = preview
    return repo


def _use_repo(app, repo):
    from app.api.v1 import link_previews as mod

    app.dependency_overrides[mod._get_repo] = lambda: repo


def _admin(app):
    admin = MagicMock()
    admin.role = "admin"
    app.dependency_overrides[get_current_user] = lambda: admin


async def _client(app):
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_get_preview_ok(test_app):
    p = _preview()
    _use_repo(test_app, _repo(p))
    async with await _client(test_app) as c:
        r = await c.get(f"/api/v1/link-previews/{p.id}")
    assert r.status_code == 200
    body = r.json()
    assert body["og_title"] == "Title"
    assert body["og_site_name"] == "Example"
    assert body["cache_ttl_seconds"] > 0
    assert "Cache-Control" in r.headers


@pytest.mark.asyncio
async def test_get_preview_not_found(test_app):
    _use_repo(test_app, _repo(None))
    async with await _client(test_app) as c:
        r = await c.get(f"/api/v1/link-previews/{uuid.uuid4()}")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_get_preview_invalid_uuid(test_app):
    async with await _client(test_app) as c:
        r = await c.get("/api/v1/link-previews/not-a-uuid")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_image_proxy_returns_image(test_app):
    p = _preview()
    _use_repo(test_app, _repo(p))
    with patch(
        "app.api.v1.link_previews.fetch_image",
        AsyncMock(return_value=(b"\x89PNG", "image/png")),
    ):
        async with await _client(test_app) as c:
            r = await c.get(f"/api/v1/link-previews/{p.id}/image")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    assert r.content == b"\x89PNG"


@pytest.mark.asyncio
async def test_image_proxy_404_without_image(test_app):
    p = _preview(image_url=None)
    _use_repo(test_app, _repo(p))
    async with await _client(test_app) as c:
        r = await c.get(f"/api/v1/link-previews/{p.id}/image")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_image_proxy_404_when_fetch_fails(test_app):
    p = _preview()
    _use_repo(test_app, _repo(p))
    with patch("app.api.v1.link_previews.fetch_image", AsyncMock(return_value=None)):
        async with await _client(test_app) as c:
            r = await c.get(f"/api/v1/link-previews/{p.id}/image")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_image_proxy_rate_limited(test_app):
    p = _preview()
    _use_repo(test_app, _repo(p))
    with patch(
        "app.api.v1.link_previews.fetch_image",
        AsyncMock(return_value=(b"x", "image/png")),
    ):
        async with await _client(test_app) as c:
            codes = [
                (await c.get(f"/api/v1/link-previews/{p.id}/image")).status_code for _ in range(70)
            ]
    assert 429 in codes


@pytest.mark.asyncio
async def test_scrape_requires_auth(test_app):
    async with await _client(test_app) as c:
        r = await c.post("/api/v1/link-previews/scrape", json={"url": "https://example.com"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_scrape_rejects_unsafe_url(test_app):
    _admin(test_app)
    with patch("app.api.v1.link_previews.is_safe_url", return_value=False):
        async with await _client(test_app) as c:
            r = await c.post("/api/v1/link-previews/scrape", json={"url": "http://127.0.0.1/x"})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_scrape_enqueues_task(test_app):
    _admin(test_app)
    with (
        patch("app.api.v1.link_previews.is_safe_url", return_value=True),
        patch("app.api.v1.link_previews.scrape_link_preview") as task,
    ):
        async with await _client(test_app) as c:
            r = await c.post("/api/v1/link-previews/scrape", json={"url": "https://example.com"})
    assert r.status_code == 202
    task.delay.assert_called_once_with("https://example.com")
