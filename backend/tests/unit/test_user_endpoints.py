"""
@file test_user_endpoints.py
@brief Unit tests for user API endpoints using httpx AsyncClient.

Tests exercise /users/me, /users/{id}, and /users routes with
mocked authentication dependencies.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings


def _make_settings() -> Settings:
    return Settings(
        SECRET_KEY="test-user-endpoints",
        JWT_ALGORITHM="HS256",
        WAF_ENABLED=False,
        ENABLE_METRICS=False,
    )


def _mock_user(**overrides) -> MagicMock:
    """@brief Build a mock User for dependency injection."""
    user = MagicMock()
    user.id = overrides.get("id", uuid.uuid4())
    user.community_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    user.email = overrides.get("email", "test@example.com")
    user.username = overrides.get("username", "testuser")
    user.display_name = overrides.get("display_name", "Test User")
    user.role = overrides.get("role", "member")
    user.is_active = True
    user.totp_enabled = False
    user.totp_secret = None
    user.email_verified = True
    user.avatar_url = None
    user.bio = None
    user.pronouns = None
    user.location = None
    user.website_url = None
    user.birthday = None
    user.storage_used = 0
    user.storage_quota = 1073741824
    user.created_at = datetime.now(UTC)
    user.updated_at = datetime.now(UTC)
    user.last_seen_at = None
    user.deleted_at = None
    return user


class TestGetMe:
    """@brief GET /api/v1/users/me tests."""

    @pytest.mark.asyncio
    async def test_returns_current_user(self, test_app):
        from app.core.dependencies import get_current_user

        user = _mock_user()

        async def _override_user():
            return user

        test_app.dependency_overrides[get_current_user] = _override_user

        try:
            transport = ASGITransport(app=test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/users/me")

            assert resp.status_code == 200
            data = resp.json()
            assert data["email"] == "test@example.com"
            assert "storage_used" in data
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self, test_app):
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/users/me")

        assert resp.status_code == 401


class TestPatchMe:
    """@brief PATCH /api/v1/users/me tests."""

    @pytest.mark.asyncio
    async def test_updates_profile(self, test_app):
        from app.core.dependencies import get_current_user

        user = _mock_user()

        async def _override_user():
            return user

        test_app.dependency_overrides[get_current_user] = _override_user

        try:
            with patch("app.api.v1.users.UserService") as mock_svc_cls:
                mock_svc = AsyncMock()
                updated = _mock_user(display_name="Updated")
                mock_svc.update_profile.return_value = updated
                mock_svc_cls.return_value = mock_svc

                transport = ASGITransport(app=test_app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.patch(
                        "/api/v1/users/me",
                        json={"display_name": "Updated"},
                    )

                assert resp.status_code == 200
        finally:
            test_app.dependency_overrides.clear()


class TestDeleteMe:
    """@brief DELETE /api/v1/users/me tests."""

    @pytest.mark.asyncio
    async def test_deactivates_account(self, test_app):
        from app.core.dependencies import get_current_user

        user = _mock_user()

        async def _override_user():
            return user

        test_app.dependency_overrides[get_current_user] = _override_user

        try:
            with patch("app.api.v1.users.UserService") as mock_svc_cls:
                mock_svc = AsyncMock()
                mock_svc_cls.return_value = mock_svc

                transport = ASGITransport(app=test_app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.delete("/api/v1/users/me")

                assert resp.status_code == 200
                mock_svc.deactivate_account.assert_called_once()
        finally:
            test_app.dependency_overrides.clear()


class TestGetUserById:
    """@brief GET /api/v1/users/{user_id} tests."""

    @pytest.mark.asyncio
    async def test_returns_public_profile(self, test_app):
        from app.core.dependencies import get_current_user

        current_user = _mock_user()
        target_user = _mock_user(
            id=uuid.uuid4(),
            username="alice",
            display_name="Alice",
        )

        async def _override_user():
            return current_user

        test_app.dependency_overrides[get_current_user] = _override_user

        try:
            with patch("app.api.v1.users.UserService") as mock_svc_cls:
                mock_svc = AsyncMock()
                mock_svc.get_user.return_value = target_user
                mock_svc_cls.return_value = mock_svc

                transport = ASGITransport(app=test_app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.get(f"/api/v1/users/{target_user.id}")

                assert resp.status_code == 200
                data = resp.json()
                assert data["username"] == "alice"
                assert "email" not in data
        finally:
            test_app.dependency_overrides.clear()
