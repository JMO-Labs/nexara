"""
@file test_moderation_api.py
@brief Unit tests for the admin NSFW moderation routes and service wiring.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1 import moderation as mod
from app.core.config import get_settings
from app.core.dependencies import get_current_user
from app.core.exceptions import NotFoundError
from app.models.user import User
from app.services.moderation_service import ModerationService

BASE = "/api/v1/admin/moderation"


@pytest.fixture
def admin() -> MagicMock:
    u = MagicMock(spec=User)
    u.id = uuid.uuid4()
    u.role = "admin"
    return u


@pytest.fixture
def svc() -> AsyncMock:
    return AsyncMock(spec=ModerationService)


@pytest.fixture
async def client(test_app, admin, svc):
    test_app.dependency_overrides[get_current_user] = lambda: admin
    test_app.dependency_overrides[mod._build_service] = lambda: svc
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://t") as c:
        yield c
    test_app.dependency_overrides.clear()


@pytest.mark.parametrize("kind,path", [("posts", "posts"), ("media", "media")])
async def test_mark_nsfw_calls_service(client, svc, admin, kind, path) -> None:
    target = uuid.uuid4()
    resp = await client.post(f"{BASE}/{path}/{target}/mark-nsfw")
    assert resp.status_code == 200
    svc.mark_nsfw.assert_awaited_once_with(kind, target, admin.id)


async def test_mark_nsfw_not_found_maps_to_404(client, svc) -> None:
    svc.mark_nsfw.side_effect = NotFoundError("Content not found")
    resp = await client.post(f"{BASE}/posts/{uuid.uuid4()}/mark-nsfw")
    assert resp.status_code == 404


async def test_mark_nsfw_requires_admin(test_app, svc) -> None:
    member = MagicMock(spec=User)
    member.id = uuid.uuid4()
    member.role = "member"
    test_app.dependency_overrides[get_current_user] = lambda: member
    test_app.dependency_overrides[mod._build_service] = lambda: svc
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://t") as c:
        resp = await c.post(f"{BASE}/media/{uuid.uuid4()}/mark-nsfw")
    test_app.dependency_overrides.clear()
    assert resp.status_code == 403
    svc.mark_nsfw.assert_not_awaited()


def test_build_service_wires_dependencies() -> None:
    settings = get_settings()
    with (
        patch.object(mod, "ModerationRepository") as repo_cls,
        patch.object(mod, "AuditRepository") as audit_cls,
    ):
        db = MagicMock()
        service = mod._build_service(db, settings)
    repo_cls.assert_called_once_with(db)
    audit_cls.assert_called_once_with(db)
    assert isinstance(service, ModerationService)
    assert service._community_id == uuid.UUID(settings.COMMUNITY_ID)
