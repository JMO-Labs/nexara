"""
@file test_oauth_oidc_admin.py
@brief Tests for POST /admin/oauth/providers/oidc and /providers/{id}/test.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

DOC = {
    "issuer": "https://kc.example.com/realms/x",
    "authorization_endpoint": "https://kc.example.com/auth",
    "token_endpoint": "https://kc.example.com/token",
    "jwks_uri": "https://kc.example.com/jwks",
}


@pytest.fixture
def admin_override(test_app):
    from app.core.dependencies import get_current_user

    user = MagicMock()
    user.id = uuid.uuid4()
    user.role = "admin"

    async def _o():
        return user

    test_app.dependency_overrides[get_current_user] = _o
    yield
    test_app.dependency_overrides.pop(get_current_user, None)


def _provider():
    p = MagicMock()
    now = datetime.now(UTC)
    vals = dict(
        id=uuid.uuid4(), community_id=uuid.uuid4(), slug="kc", display_name="KC",
        icon_url=None, provider_type="oidc", issuer=DOC["issuer"], client_id="c",
        scopes="openid profile email", authorization_endpoint=DOC["authorization_endpoint"],
        token_endpoint=DOC["token_endpoint"], userinfo_endpoint=None, jwks_uri=DOC["jwks_uri"],
        end_session_endpoint=None, group_mappings={}, default_role="member",
        group_claim="groups", avatar_claim="picture", sub_claim="sub", email_claim="email",
        name_claim="name", enabled=True, auto_create_users=True, seeded_from_env=False,
        created_at=now, updated_at=now, discovery_url="https://kc.example.com/d",
        claim_mapping={}, client_secret_encrypted="x",
    )
    for k, v in vals.items():
        setattr(p, k, v)
    return p


@pytest.mark.asyncio
async def test_register_oidc_uses_discovery_and_masks_secret(test_app, admin_override):
    prov = _provider()
    with (
        patch("app.api.v1.oauth_admin.fetch_discovery", AsyncMock(return_value=DOC)),
        patch("app.api.v1.oauth_admin.OAuthProviderRepository") as repo_cls,
        patch("app.api.v1.oauth_admin.AuditRepository") as audit_cls,
    ):
        repo = AsyncMock()
        repo.create = AsyncMock(return_value=prov)
        repo_cls.return_value = repo
        audit_cls.return_value = AsyncMock()
        async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://t") as c:
            resp = await c.post(
                "/api/v1/admin/oauth/providers/oidc",
                json={
                    "slug": "kc", "display_name": "KC", "client_id": "c",
                    "client_secret": "s3cret", "discovery_url": "https://kc.example.com/d",
                },
            )
    assert resp.status_code == 201
    assert "s3cret" not in resp.text and "client_secret" not in resp.text
    created = repo.create.call_args[0][0]
    assert created.token_endpoint == DOC["token_endpoint"]
    assert created.client_secret_encrypted != "s3cret"
    assert created.discovery_url == "https://kc.example.com/d"


@pytest.mark.asyncio
async def test_test_endpoint_reports_discovery_and_exchange(test_app, admin_override):
    prov = _provider()
    resp_mock = MagicMock(status_code=400)
    http = AsyncMock()
    http.post = AsyncMock(return_value=resp_mock)
    http.__aenter__ = AsyncMock(return_value=http)
    http.__aexit__ = AsyncMock(return_value=False)
    with (
        patch("app.api.v1.oauth_admin.fetch_discovery", AsyncMock(return_value=DOC)),
        patch("app.api.v1.oauth_admin.OAuthProviderRepository") as repo_cls,
        patch("app.api.v1.oauth_admin.httpx.AsyncClient", return_value=http),
    ):
        repo = AsyncMock()
        repo.get_by_id = AsyncMock(return_value=prov)
        repo_cls.return_value = repo
        async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://t") as c:
            resp = await c.post(f"/api/v1/admin/oauth/providers/{prov.id}/test")
    body = resp.json()
    assert resp.status_code == 200
    assert body["discovery_ok"] is True
    assert body["token_endpoint_reachable"] is True


@pytest.mark.asyncio
async def test_test_endpoint_discovery_failure(test_app, admin_override):
    prov = _provider()
    with (
        patch(
            "app.api.v1.oauth_admin.fetch_discovery",
            AsyncMock(side_effect=ValueError("Issuer must use https")),
        ),
        patch("app.api.v1.oauth_admin.OAuthProviderRepository") as repo_cls,
    ):
        repo = AsyncMock()
        repo.get_by_id = AsyncMock(return_value=prov)
        repo_cls.return_value = repo
        async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://t") as c:
            resp = await c.post(f"/api/v1/admin/oauth/providers/{prov.id}/test")
    assert resp.json()["discovery_ok"] is False
