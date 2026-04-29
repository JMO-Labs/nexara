"""
@file test_home_api.py
@brief Unit tests for GET /api/v1/home/summary and /api/v1/home/media.

Uses httpx AsyncClient with mocked HomeService and auth dependencies.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.dependencies import get_current_user

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _mock_user() -> MagicMock:
    """@brief Build a mock User for dependency injection."""
    from app.models.user import User

    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.community_id = COMMUNITY_ID
    user.last_seen_at = None
    return user


def _setup_auth_and_service(test_app, mock_service: AsyncMock):
    """@brief Override get_current_user and _build_home_service for tests."""
    from app.api.v1 import home as home_module

    user = _mock_user()

    async def _override_user():
        return user

    def _override_service():
        return mock_service

    test_app.dependency_overrides[get_current_user] = _override_user
    test_app.dependency_overrides[home_module._build_service] = _override_service
    return user


def _clear_overrides(test_app):
    """@brief Clear dependency overrides after each test."""
    test_app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_summary_unauthenticated(test_app):
    """GET /home/summary returns 401 when not authenticated."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/home/summary")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_summary_authenticated_happy_path(test_app):
    """GET /home/summary returns 200 with expected shape when authenticated."""
    from app.schemas.home import HomeSummaryResponse

    mock_svc = AsyncMock()
    mock_svc.summary.return_value = HomeSummaryResponse(
        new_posts=3,
        upcoming_events=1,
        unread_notifications=7,
    )
    _setup_auth_and_service(test_app, mock_svc)
    try:
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/home/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["new_posts"] == 3
        assert data["upcoming_events"] == 1
        assert data["unread_notifications"] == 7
    finally:
        _clear_overrides(test_app)


@pytest.mark.asyncio
async def test_media_unauthenticated(test_app):
    """GET /home/media returns 401 when not authenticated."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/home/media")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_media_authenticated_happy_path(test_app):
    """GET /home/media returns 200 with items and next_cursor when authenticated."""
    mock_svc = AsyncMock()
    mock_svc.list_media.return_value = (
        [
            {
                "media_id": str(uuid.uuid4()),
                "media": {
                    "id": str(uuid.uuid4()),
                    "filename": "photo.jpg",
                    "content_type": "image/jpeg",
                    "storage_key": "k",
                    "thumbnail_key": None,
                    "size_bytes": 100,
                    "width": 800,
                    "height": 600,
                    "duration_secs": None,
                    "alt_text": None,
                    "status": "ready",
                    "created_at": "2026-04-28T10:00:00",
                },
                "source": "post",
                "source_id": str(uuid.uuid4()),
                "source_title": "A post",
                "created_at": datetime(2026, 4, 28, 10, 0, 0, tzinfo=UTC),
            }
        ],
        None,
    )
    _setup_auth_and_service(test_app, mock_svc)
    try:
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/home/media?limit=24")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert isinstance(data["items"], list)
        assert len(data["items"]) == 1
        assert data["next_cursor"] is None
    finally:
        _clear_overrides(test_app)


@pytest.mark.asyncio
async def test_media_empty_response(test_app):
    """GET /home/media returns 200 with empty items when no media exists."""
    mock_svc = AsyncMock()
    mock_svc.list_media.return_value = ([], None)
    _setup_auth_and_service(test_app, mock_svc)
    try:
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/home/media")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["next_cursor"] is None
    finally:
        _clear_overrides(test_app)
