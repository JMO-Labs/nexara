"""
@file test_first_link_2fa.py
@brief First SSO link to an existing local account keeps its local 2FA (matrix).
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import ASGITransport, AsyncClient

from app.models.user import User
from app.services.oauth.user_provisioner import OAuthAuthResult, UserProvisioner
from tests.unit.services.test_auth_security_fixes import _make_service, _make_user

UP = "app.services.oauth.user_provisioner."


async def _provision(link):
    links, users = AsyncMock(), AsyncMock()
    u = MagicMock(spec=User)
    u.id, u.avatar_url = uuid.uuid4(), None
    links.find_by_provider_and_sub.return_value = link
    users.get_by_id.return_value = u
    users.find_by_email.return_value = u
    res = OAuthAuthResult(sub="s", email="a@b.c", email_verified=True)
    prov_cfg = MagicMock(id=uuid.uuid4(), group_mappings={}, claim_mapping={})
    with (
        patch(UP + "UserOAuthLinkRepository", return_value=links),
        patch(UP + "UserRepository", return_value=users),
        patch(UP + "apply_subgroup_mappings", AsyncMock()),
    ):
        p = UserProvisioner(AsyncMock(), uuid.uuid4())
        await p.provision_user(res, prov_cfg, "member")
    return p.linked_existing


async def test_provisioner_flags_only_the_first_link():
    assert await _provision(None) is True
    link = MagicMock(email_from_provider="a@b.c", avatar_url=None)
    assert await _provision(link) is False


async def test_login_sso_first_link_with_factor_requires_2fa():
    svc = _make_service()
    svc._issue_tokens = AsyncMock(return_value={"access_token": "a"})
    pending = {"requires_2fa": True, "two_factor_token": "p", "two_factor_methods": ["totp"]}
    with patch("app.services.auth_service.factor_methods", AsyncMock(return_value=["totp"])):
        out = await svc.login_sso(_make_user(), request=None, first_link=True)
    assert (
        out["requires_2fa"] is True and out["two_factor_methods"] == pending["two_factor_methods"]
    )
    svc._issue_tokens.assert_not_awaited()
    with (
        patch("app.services.auth_service.factor_methods", AsyncMock(return_value=["totp"])),
        patch("app.services.auth.signin_log.record_signin_safe", AsyncMock()),
    ):
        assert await svc.login_sso(_make_user(), request=None) == {"access_token": "a"}


async def test_login_sso_first_link_without_factor_issues_tokens():
    svc = _make_service()
    svc._issue_tokens = AsyncMock(return_value={"access_token": "a"})
    with (
        patch("app.services.auth_service.factor_methods", AsyncMock(return_value=[])),
        patch("app.services.auth.signin_log.record_signin_safe", AsyncMock()),
    ):
        assert await svc.login_sso(_make_user(), first_link=True) == {"access_token": "a"}


async def test_exchange_returns_pending_2fa_on_first_link(test_app):
    uid = uuid.uuid4()
    user = MagicMock(id=uid, is_active=True, memorialized_at=None)
    redis = AsyncMock()
    redis.get.return_value = f'{{"user_id": "{uid}", "provider_slug": "g", "linked_now": true}}'
    auth = MagicMock()
    auth.login_sso = AsyncMock(
        return_value={"requires_2fa": True, "two_factor_token": "p", "two_factor_methods": ["totp"]}
    )
    with (
        patch("app.api.v1.oauth._get_valkey_client", return_value=redis),
        patch("app.api.v1.oauth.AuthService", return_value=auth),
        patch("app.api.v1.oauth.UserRepository") as repo_cls,
    ):
        repo_cls.return_value.get_by_id = AsyncMock(return_value=user)
        async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://t") as c:
            r = await c.post("/api/v1/oauth/exchange", json={"code": "x"})
    assert r.status_code == 200
    body = r.json()
    assert body["requires_2fa"] is True and body["access_token"] is None
    assert body["two_factor_methods"] == ["totp"]
    assert "set-cookie" not in r.headers
    assert auth.login_sso.await_args.kwargs["first_link"] is True
