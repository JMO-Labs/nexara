"""
@file test_subgroups_list_api.py
@brief Route tests for GET /api/v1/subgroups membership flags.

Uses httpx AsyncClient with mocked SubgroupService and auth dependencies.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.dependencies import get_current_user
from tests.unit.api.test_subgroups_update_api import COMMUNITY_ID, _subgroup


@pytest.fixture
def client_setup(test_app):
    """@brief Override auth and SubgroupService; yield (app, service)."""
    from app.api.v1 import subgroups as subgroups_module
    from app.models.user import User

    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.community_id = COMMUNITY_ID
    service = MagicMock()
    service.list_subgroups_with_membership = AsyncMock()

    async def _override_user():
        return user

    test_app.dependency_overrides[get_current_user] = _override_user
    test_app.dependency_overrides[subgroups_module._build_service] = lambda: service
    yield test_app, service
    test_app.dependency_overrides.clear()


async def _get(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get("/api/v1/subgroups")


async def test_list_sets_role_and_is_member(client_setup):
    app, service = client_setup
    service.list_subgroups_with_membership.return_value = [
        (_subgroup(None), "owner"),
        (_subgroup(None), None),
    ]

    resp = await _get(app)

    assert resp.status_code == 200
    body = resp.json()
    assert [(r["my_role"], r["is_member"]) for r in body] == [("owner", True), (None, False)]


async def test_list_empty(client_setup):
    app, service = client_setup
    service.list_subgroups_with_membership.return_value = []

    resp = await _get(app)

    assert resp.status_code == 200
    assert resp.json() == []
