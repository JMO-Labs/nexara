"""
@file test_oauth_coverage_routes.py
@brief Cover remaining branches in the oauth and oauth_admin routers.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1 import oauth_admin
from app.core.exceptions import AppError, NotFoundError
from tests.integration.test_oauth_flow import _mock_provider

_CB = "/api/v1/oauth/oidc/callback"


async def _callback(test_app, provider, token_data, cookies, **patches):
    mgr = AsyncMock()
    mgr.get_provider = AsyncMock(return_value=provider)
    flow = MagicMock()
    flow.exchange_code = AsyncMock(return_value=token_data)
    with (
        patch("app.api.v1.oauth.ProviderManager", return_value=mgr),
        patch("app.api.v1.oauth.OAuthFlow", return_value=flow),
        patch("app.api.v1.oauth.get_pool", return_value=AsyncMock()),
        patch("app.api.v1.oauth.verify_id_token", AsyncMock(return_value={"sub": "s"})),
        patch("app.api.v1.oauth.UserProvisioner") as prov_cls,
    ):
        prov_cls.return_value.provision_user = AsyncMock(return_value=MagicMock(id=uuid.uuid4()))
        async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as c:
            return await c.get(
                _CB, params={"code": "c", "state": "abc"}, cookies=cookies
            )


_COOKIES = {"oauth_state": "abc", "oauth_verifier": "v", "oauth_provider": "oidc"}


async def test_callback_oidc_without_nonce_cookie_is_rejected(test_app):
    """id_token present but no nonce cookie -> Missing OAuth session."""
    resp = await _callback(test_app, _mock_provider(), {"id_token": "jwt"}, _COOKIES)
    assert resp.status_code == 401


async def test_callback_uses_custom_claim_mapping(test_app):
    """A non-empty claim_mapping routes through map_claims."""
    provider = _mock_provider()
    provider.claim_mapping = {"email": "mail"}
    provider.group_mappings = {}
    provider.default_role = "member"
    with patch("app.api.v1.oauth.map_claims") as m_map:
        m_map.return_value = SimpleNamespace(sub="s", email="e@x.com", display_name="n", groups=[])
        resp = await _callback(
            test_app, provider, {"id_token": "jwt"}, {**_COOKIES, "oauth_nonce": "n"}
        )
    assert resp.status_code == 302
    m_map.assert_called_once()


def _deps():
    return dict(
        _user=MagicMock(),
        db=MagicMock(),
        settings=SimpleNamespace(OIDC_HTTP_TIMEOUT=5, APP_BASE_URL="https://app.example.com"),
        community_id=uuid.uuid4(),
    )


async def test_create_oidc_provider_invalid_discovery_returns_422():
    """fetch_discovery ValueError is wrapped in AppError 422."""
    body = SimpleNamespace(discovery_url=" https://x.example.com ")
    with patch.object(oauth_admin, "fetch_discovery", AsyncMock(side_effect=ValueError("bad"))):
        with pytest.raises(AppError) as ei:
            await oauth_admin.create_oidc_provider(
                body, MagicMock(), user=MagicMock(), db=MagicMock(),
                settings=_deps()["settings"], community_id=uuid.uuid4(),
            )
    assert ei.value.status_code == 422


async def _run_test_provider(provider, **patches):
    d = _deps()
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=provider)
    with patch.object(oauth_admin, "OAuthProviderRepository", return_value=repo):
        return await oauth_admin.test_provider(uuid.uuid4(), **d)


async def test_test_provider_not_found():
    with pytest.raises(NotFoundError):
        await _run_test_provider(None)


async def test_test_provider_without_discovery_url():
    res = await _run_test_provider(SimpleNamespace(discovery_url=None))
    assert res.discovery_ok is False
    assert "no discovery_url" in res.error


def _provider():
    return SimpleNamespace(discovery_url="https://idp.example.com/d", client_id="cid")


def _http_client(post):
    client = AsyncMock()
    client.post = post
    client.__aenter__.return_value = client
    return client


async def test_test_provider_unexpected_status():
    client = _http_client(AsyncMock(return_value=SimpleNamespace(status_code=200)))
    doc = {"issuer": "https://idp.example.com", "token_endpoint": "https://idp.example.com/t"}
    with (
        patch.object(oauth_admin, "fetch_discovery", AsyncMock(return_value=doc)),
        patch.object(oauth_admin.httpx, "AsyncClient", return_value=client),
    ):
        res = await _run_test_provider(_provider())
    assert res.token_endpoint_reachable is False
    assert "Unexpected token endpoint status 200" in res.error


async def test_test_provider_token_endpoint_unreachable():
    client = _http_client(AsyncMock(side_effect=httpx.ConnectError("boom")))
    doc = {"issuer": "https://idp.example.com", "token_endpoint": "https://idp.example.com/t"}
    with (
        patch.object(oauth_admin, "fetch_discovery", AsyncMock(return_value=doc)),
        patch.object(oauth_admin.httpx, "AsyncClient", return_value=client),
    ):
        res = await _run_test_provider(_provider())
    assert res.error == "Token endpoint unreachable: ConnectError"
