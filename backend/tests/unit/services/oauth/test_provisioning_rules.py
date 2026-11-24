"""
@file test_provisioning_rules.py
@brief SSO JIT rules: domain/group gates, auto-create, disabled accounts, profile sync.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.core.exceptions import AuthenticationError, AuthorizationError, SsoRefusedError
from app.models.user import User
from app.services.oauth import oauth2_email
from app.services.oauth.flow import apply_verified_email
from app.services.oauth.user_provisioner import OAuthAuthResult, UserProvisioner
from tests.unit.services.oauth.helpers import sso_provider

UP = "app.services.oauth.user_provisioner."


def _user(**kw):
    u = MagicMock(spec=User)
    u.id = uuid.uuid4()
    u.role = "member"
    u.is_active = True
    u.display_name = "Ruth"
    u.email = "ruth@example.com"
    u.avatar_url = None
    u.username = "ruth"
    for k, v in kw.items():
        setattr(u, k, v)
    return u


class Env:
    """@brief Patched repos for one provision_user call."""

    def __init__(self, *, link_user=None, email_user=None, taken=()):
        self.link_repo = AsyncMock()
        self.link_repo.find_by_provider_and_sub.return_value = (
            MagicMock(user_id=link_user.id, email_from_provider=None, avatar_url=None)
            if link_user
            else None
        )
        self.users = AsyncMock()
        self.users.get_by_id.return_value = link_user
        self.users.find_by_email.return_value = email_user
        self.users.username_owner_id.return_value = None
        self.users.email_owner_id.return_value = None
        self.users.username_exists.side_effect = lambda n: n in taken
        self.users.create.side_effect = lambda u: u
        self.tokens = AsyncMock()
        self.audit = AsyncMock()

    async def run(self, auth, provider, role="member"):
        with (
            patch(UP + "UserOAuthLinkRepository", return_value=self.link_repo),
            patch(UP + "UserRepository", return_value=self.users),
            patch(UP + "TokenRepository", return_value=self.tokens),
            patch(UP + "factor_methods", AsyncMock(return_value=[])),
            patch(UP + "CalendarRepository", return_value=AsyncMock()),
            patch(UP + "HookRegistry.emit", AsyncMock()),
            patch(UP + "audit_role_synced", self.audit),
        ):
            return await UserProvisioner(AsyncMock(), uuid.uuid4()).provision_user(
                auth, provider, role
            )


def _auth(**kw):
    base = {"sub": "s1", "email": "ruth@example.com", "email_verified": True}
    return OAuthAuthResult(**{**base, **kw})


async def test_domain_not_allowed_rejected():
    env = Env()
    with pytest.raises(AuthorizationError) as exc:
        await env.run(_auth(email="a@other.com"), sso_provider(allowed_domains=["example.com"]))
    assert exc.value.code == "sso_domain_not_allowed"
    env.users.create.assert_not_called()


async def test_domain_allowed_case_insensitive():
    env = Env()
    user = await env.run(
        _auth(email="A@Example.COM"), sso_provider(allowed_domains=["example.com"])
    )
    assert user.email == "a@example.com"


async def test_required_group_missing_refused_and_tokens_revoked():
    linked = _user()
    env = Env(link_user=linked)
    with pytest.raises(SsoRefusedError) as exc:
        await env.run(_auth(groups=["other"]), sso_provider(required_group="nexara-users"))
    assert exc.value.code == "sso_group_required"
    env.tokens.revoke_all_for_user.assert_awaited_once_with(linked.id)
    env.users.update.assert_not_called()


async def test_required_group_present_passes():
    env = Env(link_user=_user())
    await env.run(_auth(groups=["nexara-users"]), sso_provider(required_group="nexara-users"))
    env.tokens.revoke_all_for_user.assert_not_called()


async def test_unknown_user_refused_without_auto_create():
    env = Env()
    with pytest.raises(SsoRefusedError) as exc:
        await env.run(_auth(), sso_provider(auto_create_users=False))
    assert exc.value.code == "sso_no_account"
    env.users.create.assert_not_called()
    env.link_repo.create.assert_not_called()


async def test_existing_email_still_links_without_auto_create():
    existing = _user()
    env = Env(email_user=existing)
    assert await env.run(_auth(), sso_provider(auto_create_users=False)) is existing
    env.link_repo.create.assert_awaited_once()


async def test_disabled_linked_user_refused_and_revoked():
    linked = _user(is_active=False)
    env = Env(link_user=linked)
    with pytest.raises(SsoRefusedError) as exc:
        await env.run(_auth(), sso_provider())
    assert exc.value.code == "sso_account_disabled"
    env.tokens.revoke_all_for_user.assert_awaited_once_with(linked.id)


async def test_disabled_email_user_not_linked():
    env = Env(email_user=_user(is_active=False))
    with pytest.raises(SsoRefusedError, match="sso_account_disabled"):
        await env.run(_auth(), sso_provider())
    env.link_repo.create.assert_not_called()


async def test_name_change_synced():
    linked = _user(display_name="Ruth")
    env = Env(link_user=linked)
    await env.run(_auth(display_name="Ruth Smith"), sso_provider())
    env.users.update.assert_awaited_once_with(linked, {"display_name": "Ruth Smith"})


async def test_sync_profile_off_leaves_profile():
    env = Env(link_user=_user())
    await env.run(
        _auth(display_name="New", avatar_url="https://a/b.png"), sso_provider(sync_profile=False)
    )
    env.users.update.assert_not_called()


async def test_email_synced_only_when_verified_and_free():
    linked = _user()
    env = Env(link_user=linked)
    await env.run(_auth(email="new@example.com", email_verified=False), sso_provider())
    env.users.update.assert_not_called()
    env.users.email_owner_id.return_value = uuid.uuid4()  # someone else (maybe deleted)
    await env.run(_auth(email="new@example.com"), sso_provider())
    env.users.update.assert_not_called()
    env.users.email_owner_id.return_value = None
    await env.run(_auth(email="New@example.com"), sso_provider())
    env.users.update.assert_awaited_once_with(
        linked, {"email": "new@example.com", "email_verified": True}
    )


async def test_username_taken_gets_suffix_on_create():
    env = Env(taken={"ruth"})
    user = await env.run(_auth(username="ruth"), sso_provider())
    assert user.username == "ruth-2"


async def test_username_synced_and_own_name_not_treated_as_taken():
    linked = _user(username="ruth-2")
    env = Env(link_user=linked, taken={"ruth", "ruth-2"})
    env.users.username_owner_id.side_effect = lambda n: linked.id if n == "ruth-2" else uuid.uuid4()
    await env.run(_auth(username="ruth"), sso_provider())
    env.users.update.assert_not_called()


async def test_role_change_audited():
    linked = _user(role="member")
    env = Env(link_user=linked)
    cm = {"group_mapping": {"admins": {"role": "admin"}}}
    await env.run(_auth(groups=["admins"]), sso_provider(claim_mapping=cm), role="admin")
    env.users.update.assert_awaited_once_with(linked, {"role": "admin"})
    env.audit.assert_awaited_once()
    assert env.audit.await_args.args[1:] == (linked.id, "member", "admin")


# ---- OAuth2 (GitHub / Discord) verified email ----


def _mock_get(monkeypatch, payload, status=200):
    calls = []

    async def fake_get(self, url, **kw):
        calls.append((url, kw))
        return httpx.Response(status, json=payload, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    return calls


async def test_github_primary_verified_email(monkeypatch):
    calls = _mock_get(
        monkeypatch,
        [
            {"email": "x@a.com", "primary": False, "verified": True},
            {"email": "p@a.com", "primary": True, "verified": True},
        ],
    )
    assert await oauth2_email.fetch_verified_email("github", "tok") == "p@a.com"
    assert calls[0][0] == "https://api.github.com/user/emails"
    assert calls[0][1]["headers"]["Authorization"] == "Bearer tok"


async def test_github_unverified_primary_returns_none(monkeypatch):
    _mock_get(monkeypatch, [{"email": "p@a.com", "primary": True, "verified": False}])
    assert await oauth2_email.fetch_verified_email("github", "tok") is None


async def test_discord_verified_flag(monkeypatch):
    _mock_get(monkeypatch, {"email": "d@a.com", "verified": True})
    assert await oauth2_email.fetch_verified_email("discord", "tok") == "d@a.com"
    _mock_get(monkeypatch, {"email": "d@a.com", "verified": False})
    assert await oauth2_email.fetch_verified_email("discord", "tok") is None


async def test_fetch_error_returns_none(monkeypatch):
    _mock_get(monkeypatch, {}, status=500)
    assert await oauth2_email.fetch_verified_email("github", "tok") is None
    assert await oauth2_email.fetch_verified_email("google", "tok") is None


async def test_github_unverified_no_link():
    """Public profile email is ignored; no verified email -> no link."""
    auth = OAuthAuthResult(sub="1", email="victim@example.com", email_verified=True)
    with patch("app.services.oauth.flow.fetch_verified_email", AsyncMock(return_value=None)):
        await apply_verified_email(sso_provider(preset="github"), {"access_token": "t"}, auth)
    assert auth.email is None and auth.email_verified is False
    env = Env(email_user=_user())
    with pytest.raises(AuthenticationError):
        await env.run(auth, sso_provider(preset="github"))
    env.link_repo.create.assert_not_called()


async def test_github_verified_email_applied():
    auth = OAuthAuthResult(sub="1", email=None)
    with patch("app.services.oauth.flow.fetch_verified_email", AsyncMock(return_value="v@a.com")):
        await apply_verified_email(sso_provider(preset="github"), {"access_token": "t"}, auth)
    assert auth.email == "v@a.com" and auth.email_verified is True


async def test_non_oauth2_preset_untouched():
    auth = OAuthAuthResult(sub="1", email="a@b.c", email_verified=True)
    with patch("app.services.oauth.flow.fetch_verified_email", AsyncMock()) as f:
        await apply_verified_email(sso_provider(preset="authentik"), {"access_token": "t"}, auth)
    f.assert_not_called()
    assert auth.email == "a@b.c"
