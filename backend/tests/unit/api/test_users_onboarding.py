"""
@file test_users_onboarding.py
@brief Unit tests for onboarding completion endpoint.

Tests the PATCH /users/me/onboarding endpoint with mocked UserService
and authentication dependencies.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1 import users as users_module
from app.core.dependencies import get_current_user


def _mock_user(**overrides) -> MagicMock:
    """@brief Build a mock User for dependency injection."""
    user = MagicMock()
    user.id = overrides.get("id", uuid.uuid4())
    user.community_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    user.username = overrides.get("username", "testuser")
    user.display_name = overrides.get("display_name", "Test User")
    user.email = overrides.get("email", "test@example.com")
    user.avatar_url = None
    user.role = overrides.get("role", "member")
    user.tour_completed_at = overrides.get("tour_completed_at", None)
    user.created_at = datetime.now(UTC)
    user.updated_at = datetime.now(UTC)
    user.totp_enabled = False
    user.storage_used = 0
    user.storage_quota = 10737418240
    user.email_verified = True
    user.last_seen_at = None
    user.bio = ""
    user.title = ""
    user.location = ""
    user.website_url = ""
    user.birthday = None
    user.pronouns = ""
    return user


def _setup_auth_and_service(test_app, mock_service: AsyncMock):
    """@brief Override get_current_user and _build_service for authenticated tests."""
    user = _mock_user()

    async def _override_user():
        return user

    def _override_service():
        return mock_service

    test_app.dependency_overrides[get_current_user] = _override_user
    test_app.dependency_overrides[users_module._build_service] = _override_service
    return user


def _clear_overrides(test_app):
    """@brief Clear dependency overrides after each test."""
    test_app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_complete_onboarding_authenticated(test_app):
    """@brief PATCH /users/me/onboarding returns 200 with updated user."""
    mock_svc = AsyncMock()
    completed_time = datetime.now(UTC)
    updated_user = _mock_user(tour_completed_at=completed_time)
    mock_svc.complete_onboarding.return_value = updated_user
    _setup_auth_and_service(test_app, mock_svc)
    try:
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.patch("/api/v1/users/me/onboarding")
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert "tour_completed_at" in data
        assert data["tour_completed_at"] is not None
        mock_svc.complete_onboarding.assert_called_once()
    finally:
        _clear_overrides(test_app)


@pytest.mark.asyncio
async def test_complete_onboarding_unauthenticated(test_app):
    """@brief PATCH /users/me/onboarding returns 401 when not authenticated."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.patch("/api/v1/users/me/onboarding")
    assert resp.status_code == 401
