"""
@file test_webhooks_api.py
@brief Route tests for per-user and admin community webhook endpoints.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1 import communities, notifications
from app.core.dependencies import get_current_user
from app.core.exceptions import NotFoundError
from app.models.webhook import WebhookSubscription
from app.services.webhook_service import WebhookService

CID = uuid.uuid4()
WID = uuid.uuid4()


def _sub(**kw):
    s = MagicMock(spec=WebhookSubscription)
    s.id, s.url, s.type_keys, s.enabled = WID, "https://x.io/h", ["a"], True
    s.failure_count, s.last_failure_at = 0, None
    s.created_at = datetime(2026, 1, 1, tzinfo=UTC)
    s.secret = "hidden"
    for k, v in kw.items():
        setattr(s, k, v)
    return s


def _user(role="member", community_id=CID):
    u = MagicMock()
    u.id, u.role, u.community_id = uuid.uuid4(), role, community_id
    return u


@pytest.fixture
def service():
    return AsyncMock(spec=WebhookService)


def _client(test_app, service, user):
    test_app.dependency_overrides[get_current_user] = lambda: user
    test_app.dependency_overrides[notifications._webhook_service] = lambda: service
    test_app.dependency_overrides[communities._webhook_service] = lambda: service
    return AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test")


@pytest.fixture
def member(test_app, service):
    yield _client(test_app, service, _user())
    test_app.dependency_overrides.clear()


@pytest.fixture
def admin(test_app, service):
    u = _user("admin")
    yield _client(test_app, service, u)
    test_app.dependency_overrides.clear()


class TestUserEndpoints:
    async def test_list_has_no_secret(self, member, service):
        service.list_for_user.return_value = [_sub()]
        async with member as c:
            r = await c.get("/api/v1/notifications/webhooks")
        assert r.status_code == 200
        body = r.json()[0]
        assert "secret" not in body
        assert set(body) == {
            "id", "url", "type_keys", "enabled", "failure_count", "last_failure_at", "created_at",
        }  # fmt: skip

    async def test_create_reveals_secret_once(self, member, service):
        service.create.return_value = (_sub(), "topsecret")
        async with member as c:
            r = await c.post(
                "/api/v1/notifications/webhooks",
                json={"url": "https://x.io/h", "type_keys": ["a"]},
            )
        assert r.status_code == 201
        assert r.json()["secret"] == "topsecret"

    async def test_create_rejects_non_http_url(self, member):
        async with member as c:
            r = await c.post(
                "/api/v1/notifications/webhooks", json={"url": "ftp://x", "type_keys": []}
            )
        assert r.status_code == 422

    async def test_patch(self, member, service):
        service.update.return_value = _sub(enabled=False)
        async with member as c:
            r = await c.patch(f"/api/v1/notifications/webhooks/{WID}", json={"enabled": False})
        assert r.status_code == 200 and r.json()["enabled"] is False

    async def test_patch_not_found(self, member, service):
        service.update.side_effect = NotFoundError()
        async with member as c:
            r = await c.patch(f"/api/v1/notifications/webhooks/{WID}", json={"enabled": True})
        assert r.status_code == 404

    async def test_delete(self, member, service):
        async with member as c:
            r = await c.delete(f"/api/v1/notifications/webhooks/{WID}")
        assert r.status_code == 200 and "message" in r.json()

    async def test_requires_auth(self, test_app):
        test_app.dependency_overrides.clear()
        async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://t") as c:
            r = await c.get("/api/v1/notifications/webhooks")
        assert r.status_code == 401


class TestAdminEndpoints:
    async def test_list(self, admin, service):
        service.list_for_community.return_value = [_sub(user_id=None)]
        async with admin as c:
            r = await c.get(f"/api/v1/communities/{CID}/webhooks")
        assert r.status_code == 200 and len(r.json()) == 1

    async def test_create(self, admin, service):
        service.create.return_value = (_sub(), "s")
        async with admin as c:
            r = await c.post(
                f"/api/v1/communities/{CID}/webhooks",
                json={"url": "https://x.io/h", "type_keys": []},
            )
        assert r.status_code == 201 and r.json()["secret"] == "s"
        assert service.create.await_args.args[0] is None

    async def test_patch_and_delete(self, admin, service):
        service.update.return_value = _sub()
        async with admin as c:
            p = await c.patch(
                f"/api/v1/communities/{CID}/webhooks/{WID}", json={"url": "https://y.io"}
            )
            d = await c.delete(f"/api/v1/communities/{CID}/webhooks/{WID}")
        assert p.status_code == 200 and d.status_code == 200
        assert service.update.await_args.args[0] is None
        assert service.delete.await_args.args[0] is None

    async def test_member_forbidden(self, member):
        async with member as c:
            r = await c.get(f"/api/v1/communities/{CID}/webhooks")
        assert r.status_code == 403

    async def test_other_community_forbidden(self, admin):
        async with admin as c:
            r = await c.get(f"/api/v1/communities/{uuid.uuid4()}/webhooks")
        assert r.status_code == 403
        assert r.json()["error"]["code"] == "WEBHOOK_FORBIDDEN"
