"""
@file test_first_link_2fa.py
@brief First SSO link to an account with a local factor is held until 2FA passes.

Matrix: (a) first link -> pending, no link row; (b) abandon + SSO again ->
still pending; (c) TOTP completes -> link created + tokens; (d) next SSO
login over the link -> tokens directly.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pyotp
from httpx import ASGITransport, AsyncClient

from app.models.user import User
from app.services.oauth.user_provisioner import OAuthAuthResult, UserProvisioner
from tests.unit.services.oauth.helpers import sso_provider
from tests.unit.services.test_auth_security_fixes import _fake_redis, _make_service, _make_user

UP = "app.services.oauth.user_provisioner."
PL = "app.services.auth.pending_link."


class World:
    """@brief One account + link table shared by provisioner and pending_link."""

    def __init__(self, user: MagicMock) -> None:
        self.user, self.links = user, []
        self.link_repo = AsyncMock()
        self.link_repo.find_by_provider_and_sub.side_effect = self._find
        self.link_repo.create.side_effect = self._create
        self.users = AsyncMock()
        self.users.get_by_id.return_value = user
        self.users.find_by_email.return_value = user

    async def _find(self, pid, sub):
        return next((x for x in self.links if x.provider_id == pid and x.sub == sub), None)

    async def _create(self, link):
        self.links.append(link)
        return link


PROVIDER = sso_provider()


async def _sso(world: World, methods: list[str]) -> UserProvisioner:
    res = OAuthAuthResult(sub="s1", email="a@b.c", email_verified=True)
    with (
        patch(UP + "UserOAuthLinkRepository", return_value=world.link_repo),
        patch(UP + "UserRepository", return_value=world.users),
        patch(UP + "factor_methods", AsyncMock(return_value=methods)),
        patch(UP + "apply_subgroup_mappings", AsyncMock()),
    ):
        p = UserProvisioner(AsyncMock(), uuid.uuid4())
        await p.provision_user(res, PROVIDER, "member")
    return p


async def test_first_link_matrix():
    secret = pyotp.random_base32()
    user = _make_user(totp_enabled=True, totp_secret=secret)
    world = World(user)
    svc = _make_service()
    svc._user_repo.get_by_id.return_value = user
    svc._issue_tokens = AsyncMock(return_value={"access_token": "a"})
    patches = (
        patch(PL + "UserOAuthLinkRepository", return_value=world.link_repo),
        patch(PL + "UserRepository", return_value=world.users),
        patch("app.services.auth_service.factor_methods", AsyncMock(return_value=["totp"])),
        patch("app.services.auth.totp_replay.get_pool", return_value=_fake_redis()),
        patch("app.services.auth.signin_log.record_signin_safe", AsyncMock()),
    )
    for p in patches:
        p.start()
    try:
        # (a) first SSO link: pending 2FA, no link row
        prov = await _sso(world, ["totp"])
        assert prov.pending_link is not None and world.links == []
        out = await svc.login_sso(user, pending_link=prov.pending_link)
        assert out["requires_2fa"] is True and world.links == []
        # (b) abandoned; SSO again is still pending
        prov = await _sso(world, ["totp"])
        assert prov.pending_link is not None
        out = await svc.login_sso(user, pending_link=prov.pending_link)
        assert out["requires_2fa"] is True and world.links == []
        # (c) complete TOTP: link created, tokens issued
        code = pyotp.TOTP(secret).now()
        tokens = await svc.verify_2fa_login(two_factor_token=out["two_factor_token"], code=code)
        assert tokens == {"access_token": "a"}
        assert len(world.links) == 1 and world.links[0].sub == "s1"
        assert world.links[0].user_id == user.id
        # (d) next SSO login goes over the link: tokens directly
        prov = await _sso(world, ["totp"])
        assert prov.pending_link is None
        assert await svc.login_sso(user, pending_link=prov.pending_link) == {"access_token": "a"}
    finally:
        for p in patches:
            p.stop()


async def test_first_link_without_factor_links_immediately():
    user = MagicMock(spec=User)
    user.id, user.avatar_url, user.role = uuid.uuid4(), None, "member"
    world = World(user)
    prov = await _sso(world, [])
    assert prov.pending_link is None and len(world.links) == 1


async def test_create_link_is_idempotent_and_noop_without_link():
    from app.services.auth.pending_link import create_link

    links = AsyncMock()
    with patch(PL + "UserOAuthLinkRepository", return_value=links):
        await create_link(AsyncMock(), uuid.uuid4(), None)
        links.find_by_provider_and_sub.return_value = MagicMock()
        await create_link(AsyncMock(), uuid.uuid4(), {"provider_id": str(uuid.uuid4()), "sub": "s"})
    links.create.assert_not_awaited()


def _real_exchange(auth, user):
    """@brief AuthService factory: real exchange_sso resolution, stubbed login_sso."""
    from app.services.auth_service import AuthService

    def make(db, settings):
        svc = AuthService.__new__(AuthService)
        svc._user_repo = MagicMock(get_by_id=AsyncMock(return_value=user))
        svc.login_sso = auth.login_sso  # type: ignore[method-assign]
        return svc

    return make


async def test_exchange_returns_pending_2fa_for_held_link(test_app):
    uid = uuid.uuid4()
    user = MagicMock(id=uid, is_active=True, memorialized_at=None)
    redis = AsyncMock()
    redis.getdel.return_value = (
        f'{{"user_id": "{uid}", "provider_slug": "g", "pending_link": {{"sub": "s"}}}}'
    )
    auth = MagicMock()
    auth.login_sso = AsyncMock(
        return_value={"requires_2fa": True, "two_factor_token": "p", "two_factor_methods": ["totp"]}
    )
    with (
        patch("app.api.v1.oauth._get_valkey_client", return_value=redis),
        patch("app.api.v1.oauth.AuthService", side_effect=_real_exchange(auth, user)),
    ):
        async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://t") as c:
            r = await c.post("/api/v1/oauth/exchange", json={"code": "x"})
    assert r.status_code == 200
    body = r.json()
    assert body["requires_2fa"] is True and body["access_token"] is None
    assert "set-cookie" not in r.headers
    assert auth.login_sso.await_args.kwargs["pending_link"] == {"sub": "s"}
