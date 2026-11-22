"""
@file test_capsule_media_guard.py
@brief Sealed-capsule media is 404 for non-authors and served after opening;
       capsule GET for a recipient has no ``body`` key.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

from httpx import ASGITransport, AsyncClient

from app.api.v1.media import _build_service as media_build
from app.api.v1.time_capsules import _build_service as capsule_build
from app.core.dependencies import get_current_user, get_optional_user
from app.models.media import Media
from app.repositories.media_repo import MediaRepository
from app.repositories.time_capsule_repo import TimeCapsuleRepository
from app.schemas.time_capsule import CapsuleAuthor, CapsuleSealed
from app.services.media_service import MediaService
from app.services.storage.base import StorageBackend

CID = uuid.UUID("00000000-0000-0000-0000-000000000001")
MAYA, AUTHOR = uuid.uuid4(), uuid.uuid4()


def _user(uid: uuid.UUID) -> MagicMock:
    u = MagicMock()
    u.id = uid
    return u


def _media_service(sealed_for: set[uuid.UUID | None]) -> MediaService:
    repo = AsyncMock(spec=MediaRepository)
    m = MagicMock(spec=Media)
    m.storage_key, m.content_type, m.thumbnail_key = "k", "image/png", "t"
    repo.get.return_value = m
    storage = AsyncMock(spec=StorageBackend)
    storage.get.return_value = b"PNG"
    caps = AsyncMock(spec=TimeCapsuleRepository)
    caps.is_sealed_media.side_effect = lambda mid, cid, viewer: viewer in sealed_for
    return MediaService(repo, storage, MagicMock(), CID, capsule_repo=caps)


async def _get(app, path: str) -> int:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        return (await c.get(f"/api/v1{path}")).status_code


async def test_sealed_media_404_for_maya_and_anon_ok_for_author_and_after_open(test_app) -> None:
    mid = uuid.uuid4()
    state = {"sealed_for": {MAYA, None}}
    test_app.dependency_overrides[media_build] = lambda: _media_service(state["sealed_for"])
    test_app.dependency_overrides[get_optional_user] = lambda: _user(MAYA)
    assert await _get(test_app, f"/media/{mid}/file") == 404
    assert await _get(test_app, f"/media/{mid}/thumbnail") == 404
    test_app.dependency_overrides[get_optional_user] = lambda: None
    assert await _get(test_app, f"/media/{mid}/file") == 404
    test_app.dependency_overrides[get_optional_user] = lambda: _user(AUTHOR)
    assert await _get(test_app, f"/media/{mid}/file") == 200
    state["sealed_for"] = set()  # capsule opened
    test_app.dependency_overrides[get_optional_user] = lambda: _user(MAYA)
    assert await _get(test_app, f"/media/{mid}/file") == 200


async def test_sealed_capsule_json_has_no_body_key(test_app) -> None:
    from datetime import UTC, datetime

    svc = AsyncMock()
    svc.get.return_value = CapsuleSealed(
        id=uuid.uuid4(),
        title="t",
        author=CapsuleAuthor(id=AUTHOR, display_name="Ruth"),
        open_at=datetime.now(UTC),
        recipients_summary="1 people",
    )
    test_app.dependency_overrides[capsule_build] = lambda: svc
    test_app.dependency_overrides[get_current_user] = lambda: _user(MAYA)
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://t") as c:
        r = await c.get(f"/api/v1/capsules/{uuid.uuid4()}")
    assert r.status_code == 200
    assert "body" not in r.json() and "media" not in r.json()
