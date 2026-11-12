"""
@file test_user_profile.py
@brief Integration tests for the pronouns profile field via the users API.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.dependencies import get_current_user, get_db


def _user(pronouns: str | None = None) -> MagicMock:
    """@brief Build a mock User with all response fields populated."""
    u = MagicMock()
    u.id = uuid.uuid4()
    u.community_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    u.email = "t@example.com"
    u.username = "tester"
    u.display_name = "Tester"
    u.role = "member"
    u.is_active = True
    u.totp_enabled = False
    u.email_verified = True
    u.avatar_url = u.bio = u.title = u.location = u.website_url = None
    u.birthday = u.last_seen_at = u.tour_completed_at = u.deleted_at = None
    u.pronouns = pronouns
    u.storage_used = 0
    u.storage_quota = 1
    u.created_at = u.updated_at = datetime.now(UTC)
    return u


@pytest.fixture
def client_for(test_app):
    """@brief Factory yielding a client authenticated as a given user."""

    def _make(user: MagicMock) -> AsyncClient:
        test_app.dependency_overrides[get_current_user] = lambda: user
        test_app.dependency_overrides[get_db] = lambda: AsyncMock()
        return AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test")

    yield _make
    test_app.dependency_overrides.clear()


class TestPronouns:
    """@brief Pronouns field on user profile endpoints."""

    async def test_me_includes_pronouns(self, client_for):
        async with client_for(_user("they/them")) as c:
            resp = await c.get("/api/v1/users/me")
        assert resp.status_code == 200
        assert resp.json()["pronouns"] == "they/them"

    async def test_patch_saves_pronouns(self, client_for):
        user = _user()
        updated = _user("she/her")
        with patch("app.api.v1.users.UserService") as svc_cls:
            svc_cls.return_value.update_profile = AsyncMock(return_value=updated)
            async with client_for(user) as c:
                resp = await c.patch("/api/v1/users/me", json={"pronouns": "she/her"})
            sent = svc_cls.return_value.update_profile.call_args.args[1]
        assert resp.status_code == 200
        assert resp.json()["pronouns"] == "she/her"
        assert sent["pronouns"] == "she/her"

    async def test_patch_rejects_over_50_chars(self, client_for):
        async with client_for(_user()) as c:
            resp = await c.patch("/api/v1/users/me", json={"pronouns": "x" * 51})
        assert resp.status_code == 422

    async def test_patch_accepts_exactly_50_chars(self, client_for):
        with patch("app.api.v1.users.UserService") as svc_cls:
            svc_cls.return_value.update_profile = AsyncMock(return_value=_user("x" * 50))
            async with client_for(_user()) as c:
                resp = await c.patch("/api/v1/users/me", json={"pronouns": "x" * 50})
        assert resp.status_code == 200

    async def test_public_profile_includes_pronouns(self, client_for):
        target = _user("he/him")
        with patch("app.api.v1.users.UserService") as svc_cls:
            svc_cls.return_value.get_user = AsyncMock(return_value=target)
            svc_cls.return_value.get_public_profile = AsyncMock(return_value=target)
            async with client_for(_user()) as c:
                resp = await c.get(f"/api/v1/users/{target.id}")
        assert resp.status_code == 200
        assert resp.json()["pronouns"] == "he/him"
