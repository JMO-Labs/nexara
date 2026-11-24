"""
@file test_media_nsfw_routes.py
@brief Unit: every upload path (form upload, URL import, multipart complete)
       prechecks an NSFW flag before storing and flags it in the same request.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1 import media as media_api
from app.core.dependencies import get_current_user
from app.core.exceptions import AuthorizationError


@pytest.fixture
async def env(test_app):
    user = MagicMock(id=uuid.uuid4(), role="member")
    svc = MagicMock()
    media_id = uuid.uuid4()
    svc.complete_multipart_upload = AsyncMock(return_value=MagicMock(id=media_id))
    test_app.dependency_overrides[get_current_user] = lambda: user
    test_app.dependency_overrides[media_api._build_service] = lambda: svc
    nsfw = MagicMock(precheck_flag=AsyncMock(), set_media_nsfw=AsyncMock())
    out = MagicMock(id=media_id)
    with (
        patch.object(media_api, "media_nsfw", nsfw),
        patch.object(media_api, "import_image_from_url", AsyncMock(return_value=out)),
    ):
        async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://t") as c:
            yield c, nsfw, svc, user, media_id
    test_app.dependency_overrides.clear()


async def test_import_url_flags_nsfw(env) -> None:
    c, nsfw, svc, user, mid = env
    nsfw.set_media_nsfw.return_value = {
        "id": str(mid), "filename": "a", "content_type": "image/png", "storage_key": "k",
        "size_bytes": 1, "status": "ready", "created_at": "2026-01-01T00:00:00Z", "is_nsfw": True,
    }  # fmt: skip
    r = await c.post(
        "/api/v1/media/import-url", json={"url": "https://x.test/a.png", "is_nsfw": True}
    )
    assert r.status_code == 201
    nsfw.precheck_flag.assert_awaited_once_with(svc, user)
    nsfw.set_media_nsfw.assert_awaited_once_with(svc, user, mid, True)


async def test_import_url_rejected_before_download(env) -> None:
    c, nsfw, _svc, _user, _mid = env
    nsfw.precheck_flag.side_effect = AuthorizationError("adults only")
    r = await c.post(
        "/api/v1/media/import-url", json={"url": "https://x.test/a.png", "is_nsfw": True}
    )
    assert r.status_code == 403
    media_api.import_image_from_url.assert_not_awaited()


async def test_multipart_complete_flags_nsfw(env) -> None:
    c, nsfw, svc, user, mid = env
    r = await c.post("/api/v1/media/upload/abc/complete?is_nsfw=true")
    assert r.status_code == 200
    nsfw.precheck_flag.assert_awaited_once_with(svc, user)
    nsfw.set_media_nsfw.assert_awaited_once_with(svc, user, mid, True)


async def test_multipart_complete_default_not_flagged(env) -> None:
    c, nsfw, _svc, _user, _mid = env
    r = await c.post("/api/v1/media/upload/abc/complete")
    assert r.status_code == 200
    nsfw.precheck_flag.assert_not_awaited()
    nsfw.set_media_nsfw.assert_not_awaited()
