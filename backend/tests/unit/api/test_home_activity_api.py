"""
@file test_home_activity_api.py
@brief Tests for GET /api/v1/home/activity endpoint.

Smoke tests: auth required, correct response shape, pagination.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.dependencies import get_current_user
from app.schemas.activity import ActivityFeedResponse

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _mock_user() -> MagicMock:
    """@brief Build a mock User for dependency injection."""
    from app.models.user import User

    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.community_id = COMMUNITY_ID
    return user


def _setup_auth_and_service(test_app, mock_service: AsyncMock):
    """@brief Override get_current_user and _build_activity_service for tests."""
    from app.api.v1 import home_activity as activity_module

    user = _mock_user()

    async def _override_user():
        return user

    def _override_service():
        return mock_service

    test_app.dependency_overrides[get_current_user] = _override_user
    test_app.dependency_overrides[activity_module._build_service] = _override_service
    return user


def _clear_overrides(test_app):
    """@brief Clear dependency overrides after each test."""
    test_app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_activity_unauthenticated(test_app):
    """GET /api/v1/home/activity returns 401 when not authenticated."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/home/activity")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_activity_authenticated_happy_path(test_app):
    """GET /api/v1/home/activity returns 200 with expected schema when authenticated."""
    mock_svc = AsyncMock()
    mock_svc.list_for_user.return_value = ActivityFeedResponse(
        items=[],
        next_cursor=None,
    )
    _setup_auth_and_service(test_app, mock_svc)
    try:
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/home/activity")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "next_cursor" in data
        assert isinstance(data["items"], list)
    finally:
        _clear_overrides(test_app)


@pytest.mark.asyncio
async def test_activity_with_limit_parameter(test_app):
    """Limit parameter is passed to service."""
    mock_svc = AsyncMock()
    mock_svc.list_for_user.return_value = ActivityFeedResponse(
        items=[],
        next_cursor=None,
    )
    _setup_auth_and_service(test_app, mock_svc)
    try:
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/home/activity?limit=50")
        assert resp.status_code == 200
        # Verify service was called with the limit
        mock_svc.list_for_user.assert_called_once()
        call_kwargs = mock_svc.list_for_user.call_args.kwargs
        assert call_kwargs["limit"] == 50
    finally:
        _clear_overrides(test_app)


@pytest.mark.asyncio
async def test_activity_validates_limit(test_app):
    """Limit must be >=1 and <=100."""
    mock_svc = AsyncMock()
    mock_svc.list_for_user.return_value = ActivityFeedResponse(items=[], next_cursor=None)
    _setup_auth_and_service(test_app, mock_svc)
    try:
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Limit too high
            resp = await client.get("/api/v1/home/activity?limit=101")
            assert resp.status_code == 422

            # Limit too low
            resp = await client.get("/api/v1/home/activity?limit=0")
            assert resp.status_code == 422
    finally:
        _clear_overrides(test_app)
