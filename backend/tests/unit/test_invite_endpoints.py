"""
@file test_invite_endpoints.py
@brief Unit tests for admin invite API endpoints.

Tests cover invite creation, listing, and deletion with mocked
authentication and service dependencies.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings


def _make_settings() -> Settings:
    return Settings(
        SECRET_KEY="test-invite-endpoints",
        JWT_ALGORITHM="HS256",
        WAF_ENABLED=False,
        ENABLE_METRICS=False,
    )


def _mock_admin() -> MagicMock:
    """@brief Build a mock admin User for dependency injection."""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.community_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    user.email = "admin@example.com"
    user.username = "admin"
    user.display_name = "Admin"
    user.role = "admin"
    user.is_active = True
    user.deleted_at = None
    return user


def _mock_member() -> MagicMock:
    """@brief Build a mock member User for auth testing."""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.community_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    user.role = "member"
    user.is_active = True
    user.deleted_at = None
    return user


class TestCreateInvite:
    """@brief POST /api/v1/admin/invites tests."""

    @pytest.mark.asyncio
    async def test_admin_creates_invite(self, test_app):
        from app.core.dependencies import get_current_user

        admin = _mock_admin()

        async def _override():
            return admin

        test_app.dependency_overrides[get_current_user] = _override

        now = datetime.now(UTC)

        class FakeInvite:
            """Simple object to satisfy Pydantic from_attributes validation."""
            pass

        mock_invite = FakeInvite()
        mock_invite.id = uuid.uuid4()
        mock_invite.email = "new@example.com"
        mock_invite.role = "member"
        mock_invite.created_by = admin.id
        mock_invite.expires_at = now + timedelta(days=7)
        mock_invite.used_at = None
        mock_invite.created_at = now
        mock_invite.raw_token = "placeholder"

        try:
            with patch("app.api.v1.invites.InviteRepository") as mock_repo_cls:
                mock_repo = AsyncMock()
                mock_repo.create.return_value = mock_invite
                mock_repo_cls.return_value = mock_repo

                transport = ASGITransport(app=test_app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.post(
                        "/api/v1/admin/invites",
                        json={"email": "new@example.com", "role": "member"},
                    )

                assert resp.status_code == 201
                data = resp.json()
                assert data["email"] == "new@example.com"
                assert "raw_token" in data
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_member_cannot_create_invite(self, test_app):
        from app.core.dependencies import get_current_user

        member = _mock_member()

        async def _override():
            return member

        test_app.dependency_overrides[get_current_user] = _override

        try:
            transport = ASGITransport(app=test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/admin/invites",
                    json={"email": "new@example.com"},
                )

            assert resp.status_code == 403
        finally:
            test_app.dependency_overrides.clear()


class TestListInvites:
    """@brief GET /api/v1/admin/invites tests."""

    @pytest.mark.asyncio
    async def test_admin_lists_invites(self, test_app):
        from app.core.dependencies import get_current_user

        admin = _mock_admin()

        async def _override():
            return admin

        test_app.dependency_overrides[get_current_user] = _override

        try:
            with patch("app.api.v1.invites.InviteRepository") as mock_repo_cls:
                mock_repo = AsyncMock()
                mock_repo.list_active.return_value = []
                mock_repo_cls.return_value = mock_repo

                transport = ASGITransport(app=test_app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.get("/api/v1/admin/invites")

                assert resp.status_code == 200
                data = resp.json()
                assert isinstance(data, list)
        finally:
            test_app.dependency_overrides.clear()


class TestDeleteInvite:
    """@brief DELETE /api/v1/admin/invites/{id} tests."""

    @pytest.mark.asyncio
    async def test_admin_deletes_invite(self, test_app):
        from app.core.dependencies import get_current_user

        admin = _mock_admin()

        async def _override():
            return admin

        test_app.dependency_overrides[get_current_user] = _override

        invite_id = uuid.uuid4()

        try:
            with patch("app.api.v1.invites.InviteRepository") as mock_repo_cls:
                mock_repo = AsyncMock()
                mock_repo.delete_invite.return_value = True
                mock_repo_cls.return_value = mock_repo

                transport = ASGITransport(app=test_app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.delete(f"/api/v1/admin/invites/{invite_id}")

                assert resp.status_code == 200
        finally:
            test_app.dependency_overrides.clear()
