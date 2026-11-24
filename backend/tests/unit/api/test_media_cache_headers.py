"""
@file test_media_cache_headers.py
@brief Unit: per-viewer media responses vary on auth; NSFW media is never cached.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1 import media as media_api


@pytest.fixture
async def client(test_app):
    svc = MagicMock()
    svc.get_file_public = AsyncMock(return_value=(b"IMG", "image/jpeg"))
    svc.get_thumbnail = AsyncMock(return_value=(b"IMG", "image/webp"))
    svc.is_nsfw = AsyncMock(return_value=False)
    test_app.dependency_overrides[media_api._build_service] = lambda: svc
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://t") as c:
        yield c, svc
    test_app.dependency_overrides.clear()


@pytest.mark.parametrize("kind", ["file", "thumbnail"])
async def test_safe_media_cached_privately_and_varies(client, kind) -> None:
    c, _svc = client
    r = await c.get(f"/api/v1/media/{uuid.uuid4()}/{kind}")
    assert r.status_code == 200
    assert r.headers["vary"].startswith("Authorization, Cookie")
    assert r.headers["cache-control"].startswith("private, max-age=")


@pytest.mark.parametrize("kind", ["file", "thumbnail"])
async def test_nsfw_media_not_stored(client, kind) -> None:
    c, svc = client
    svc.is_nsfw.return_value = True
    r = await c.get(f"/api/v1/media/{uuid.uuid4()}/{kind}")
    assert r.headers["cache-control"] == "private, no-store"
    assert r.headers["vary"].startswith("Authorization, Cookie")
