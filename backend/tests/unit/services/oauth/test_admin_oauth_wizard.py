"""
@file test_admin_oauth_wizard.py
@brief Admin SSO wizard backend: callback URL and discovery on create/update.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.config import Settings
from app.core.exceptions import NotFoundError
from app.models.oauth_provider import OAuthProvider
from app.schemas.oauth import OAuthProviderCreate, OAuthProviderUpdate
from app.services.oauth.admin_oauth_service import AdminOAuthService
from app.services.oauth.public_url import callback_url, public_base

DOC = {
    "issuer": "https://auth.example.com/application/o/nexara/",
    "authorization_endpoint": "https://auth.example.com/authorize",
    "token_endpoint": "https://auth.example.com/token",
    "jwks_uri": "https://auth.example.com/jwks",
}
URL = "https://auth.example.com/application/o/nexara/.well-known/openid-configuration"
MOD = "app.services.oauth.admin_oauth_service"


def _settings(**kw: str) -> Settings:
    return Settings(SECRET_KEY="k", **kw)  # type: ignore[arg-type]


def test_callback_url_prefers_allowed_origin():
    s = _settings(ALLOWED_ORIGINS="https://home.example.com/", APP_BASE_URL="https://x.io")
    assert callback_url(s, "kc") == "https://home.example.com/api/v1/oauth/kc/callback"


def test_callback_url_falls_back_to_app_base_url():
    s = _settings(APP_BASE_URL="https://nexara.example.com/")
    assert public_base(s) == "https://nexara.example.com"


def _svc() -> tuple[AdminOAuthService, AsyncMock]:
    repo = AsyncMock()
    repo.create.side_effect = lambda p: p
    repo.update.side_effect = lambda p, data: MagicMock(id=uuid.uuid4(), slug="s", **data)
    with patch(f"{MOD}.OAuthProviderRepository", return_value=repo):
        svc = AdminOAuthService(MagicMock(), uuid.uuid4(), _settings(), uuid.uuid4(), None)
    return svc, repo


@patch(f"{MOD}.AuditRepository")
@patch(f"{MOD}.fetch_discovery", new_callable=AsyncMock, return_value=DOC)
async def test_create_with_discovery_url_uses_document_issuer(_fetch, _audit):
    _audit.return_value.append = AsyncMock()
    svc, _repo = _svc()
    body = OAuthProviderCreate(
        slug="authentik",
        display_name="authentik",
        provider_type="oidc",
        client_id="c",
        client_secret="s",
        discovery_url=URL,
        preset="authentik",
    )
    p = await svc.create(body)
    assert p.issuer == DOC["issuer"]  # exact, trailing slash kept (ID token iss)
    assert p.token_endpoint == DOC["token_endpoint"]
    assert p.discovery_url == URL


@patch(f"{MOD}.AuditRepository")
@patch(f"{MOD}.fetch_discovery", new_callable=AsyncMock, return_value=DOC)
async def test_update_new_discovery_url_refreshes_endpoints(_fetch, _audit):
    _audit.return_value.append = AsyncMock()
    svc, repo = _svc()
    current = MagicMock(spec=OAuthProvider, discovery_url="https://old", provider_type="oidc")
    repo.get_by_id.return_value = current
    out = await svc.update(uuid.uuid4(), OAuthProviderUpdate(discovery_url=URL))
    assert out.issuer == DOC["issuer"]
    assert out.authorization_endpoint == DOC["authorization_endpoint"]


async def test_read_test_result_missing_is_not_found():
    svc, _ = _svc()
    with (
        patch(f"{MOD}.get_pool"),
        patch(f"{MOD}.sso_test_login.read_result", new_callable=AsyncMock, return_value=None),
        pytest.raises(NotFoundError),
    ):
        await svc.read_test_result("nope")
