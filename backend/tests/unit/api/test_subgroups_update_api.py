"""
@file test_subgroups_update_api.py
@brief Route tests for PUT /api/v1/subgroups/{slug} payload filtering.

Uses httpx AsyncClient with mocked SubgroupService and auth dependencies.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.dependencies import get_current_user

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _subgroup(accent: str | None) -> MagicMock:
    """@brief Build a subgroup-like mock with all detail-response fields."""
    now = datetime.now(UTC)
    sg = MagicMock()
    sg.id = uuid.uuid4()
    sg.name = "Hikers"
    sg.slug = "hikers"
    sg.description = None
    sg.avatar_url = None
    sg.cover_media_id = None
    sg.accent_color = accent
    sg.is_private = False
    sg.join_policy = "open"
    sg.created_by = None
    sg.archived_at = None
    sg.created_at = now
    sg.updated_at = now
    return sg


@pytest.fixture
def client_setup(test_app):
    """@brief Override auth and SubgroupService; yield (app, user, service)."""
    from app.api.v1 import subgroups as subgroups_module
    from app.models.user import User

    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.community_id = COMMUNITY_ID
    service = MagicMock()
    service.update_subgroup = AsyncMock()
    service.get_pinned_post_id = AsyncMock(return_value=None)
    service._member_repo.count_members = AsyncMock(return_value=1)
    service._member_repo.get_membership = AsyncMock(return_value=None)
    service._subgroup_repo.get_chat_channel = AsyncMock(return_value=None)

    async def _override_user():
        return user

    test_app.dependency_overrides[get_current_user] = _override_user
    test_app.dependency_overrides[subgroups_module._build_service] = lambda: service
    yield test_app, user, service
    test_app.dependency_overrides.clear()


async def _put(app, url: str, payload: dict):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.put(url, json=payload)


async def test_update_keeps_explicit_null_accent_and_parent(client_setup):
    app, user, service = client_setup
    service.update_subgroup.return_value = _subgroup(None)

    resp = await _put(
        app,
        "/api/v1/subgroups/hikers",
        {"accent_color": None, "parent_id": None, "description": None},
    )

    assert resp.status_code == 200
    assert resp.json()["accent_color"] is None
    service.update_subgroup.assert_awaited_once_with(
        "hikers", user, {"accent_color": None, "parent_id": None}
    )


async def test_update_passes_accent_value(client_setup):
    app, user, service = client_setup
    service.update_subgroup.return_value = _subgroup("#FFFFFF")

    resp = await _put(app, "/api/v1/subgroups/hikers", {"accent_color": "#FFFFFF"})

    assert resp.status_code == 200
    assert resp.json()["accent_color"] == "#FFFFFF"
    service.update_subgroup.assert_awaited_once_with("hikers", user, {"accent_color": "#FFFFFF"})


async def test_update_rejects_malformed_accent(client_setup):
    app, _, service = client_setup

    resp = await _put(app, "/api/v1/subgroups/hikers", {"accent_color": "red"})

    assert resp.status_code == 422
    service.update_subgroup.assert_not_awaited()
