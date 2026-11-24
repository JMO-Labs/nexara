"""
@file test_provisioning_hardening.py
@brief Review round 1: verified-only domain gate, preset username claims, email-sync
       mitigations, pre-account hijack guard, username race retry, deleted link target.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import AppError, SsoRefusedError
from app.schemas.oauth import OAuthProviderCreate
from app.services.oauth import admin_oauth_service as admin_mod
from app.services.oauth.email_change import notify_email_synced
from app.services.oauth.presets import PRESETS
from app.services.oauth.profile_sync import sync_profile
from app.services.oauth.user_provisioner import OAuthAuthResult
from tests.unit.services.oauth.helpers import sso_provider
from tests.unit.services.oauth.test_provisioning_rules import Env, _auth, _user

UP = "app.services.oauth.user_provisioner."
EC = "app.services.oauth.email_change."


# ---- 1. domain gate trusts verified email only ----


async def test_linked_user_unverified_allowed_domain_refused_and_revoked():
    linked = _user()
    env = Env(link_user=linked)
    with pytest.raises(SsoRefusedError) as exc:
        await env.run(
            _auth(email="x@allowed.com", email_verified=False),
            sso_provider(allowed_domains=["allowed.com"]),
        )
    assert exc.value.code == "sso_domain_not_allowed"
    env.tokens.revoke_all_for_user.assert_awaited_once_with(linked.id)


async def test_linked_user_left_domain_refused_and_revoked():
    linked = _user()
    env = Env(link_user=linked)
    with pytest.raises(SsoRefusedError, match="sso_domain_not_allowed"):
        await env.run(_auth(email="x@other.com"), sso_provider(allowed_domains=["allowed.com"]))
    env.tokens.revoke_all_for_user.assert_awaited_once_with(linked.id)


# ---- 2. preset username claims ----


def test_preset_username_claims():
    assert PRESETS["github"].username_claim == "login"
    assert PRESETS["discord"].username_claim == "username"
    assert PRESETS["authentik"].username_claim == "preferred_username"


def _svc():
    settings = SimpleNamespace(OIDC_HTTP_TIMEOUT=5, APP_BASE_URL="https://a", SECRET_KEY="k")
    svc = admin_mod.AdminOAuthService(MagicMock(), uuid.uuid4(), settings, uuid.uuid4(), None)  # type: ignore[arg-type]
    svc._repo = MagicMock(  # type: ignore[assignment]
        create=AsyncMock(side_effect=lambda p: p), find_by_slug=AsyncMock(return_value=None)
    )
    svc._audit = AsyncMock()  # type: ignore[method-assign]
    return svc


def _body(**kw):
    base = {
        "slug": "gh",
        "display_name": "GitHub",
        "provider_type": "oauth2",
        "client_id": "c",
        "client_secret": "s",
    }
    return OAuthProviderCreate(**{**base, **kw})


async def test_create_from_preset_applies_username_claim():
    assert (await _svc().create(_body(preset="github"))).username_claim == "login"
    assert (await _svc().create(_body(preset="discord"))).username_claim == "username"


async def test_explicit_username_claim_wins_over_preset():
    p = await _svc().create(_body(preset="github", username_claim="email"))
    assert p.username_claim == "email"


# ---- 3. email sync mitigations ----


async def test_email_sync_triggers_notice():
    user = _user(email="old@example.com")
    users = AsyncMock()
    users.email_owner_id.return_value = None
    users.username_owner_id.return_value = None
    notify = AsyncMock()
    with patch("app.services.oauth.profile_sync.notify_email_synced", notify):
        await sync_profile(
            users,
            user,
            OAuthAuthResult(sub="s", email="new@example.com", email_verified=True),
            session=MagicMock(),
            community_id=uuid.uuid4(),
            provider_id=uuid.uuid4(),
        )
    notify.assert_awaited_once()
    args = notify.await_args.kwargs
    assert (args["old_email"], args["new_email"]) == ("old@example.com", "new@example.com")


async def test_notify_email_synced_audits_revokes_and_mails_old_address():
    uid, pid, cid = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    audit, tokens, branding = AsyncMock(), AsyncMock(), AsyncMock()
    branding.get.return_value = MagicMock(community_name="Smith <Family>")
    send = MagicMock()
    with (
        patch(EC + "AuditRepository", return_value=audit),
        patch(EC + "TokenRepository", return_value=tokens),
        patch(EC + "BrandingRepository", return_value=branding),
        patch(EC + "send_email", send),
    ):
        await notify_email_synced(
            MagicMock(),
            user_id=uid,
            community_id=cid,
            provider_id=pid,
            old_email="old@example.com",
            new_email="new@example.com",
        )
    audit.append.assert_awaited_once()
    a = audit.append.await_args.kwargs
    assert a["action"] == "sso.email_synced" and a["target_id"] == uid
    assert a["extra_data"] == {
        "old_email": "old@example.com",
        "new_email": "new@example.com",
        "provider_id": str(pid),
    }
    tokens.revoke_all_for_user.assert_awaited_once_with(uid)  # reset tokens live here
    tokens.revoke_magic_links_for_user.assert_awaited_once_with(uid)
    kw = send.delay.call_args.kwargs
    assert kw["to"] == "old@example.com"
    assert kw["subject"] == "Your Smith <Family> email was changed"
    assert "sign-in provider" in kw["text_body"] and "admin" in kw["text_body"]
    assert "&lt;Family&gt;" in kw["html_body"]


async def test_notify_survives_broker_down():
    send = MagicMock()
    send.delay.side_effect = RuntimeError("broker")
    with (
        patch(EC + "AuditRepository", return_value=AsyncMock()),
        patch(EC + "TokenRepository", return_value=AsyncMock()),
        patch(EC + "BrandingRepository", return_value=AsyncMock(get=AsyncMock(return_value=None))),
        patch(EC + "send_email", send),
    ):
        await notify_email_synced(
            MagicMock(),
            user_id=uuid.uuid4(),
            community_id=uuid.uuid4(),
            provider_id=None,
            old_email="o@x.com",
            new_email="n@x.com",
        )


# ---- 4. pre-account hijack ----


async def test_unverified_local_account_not_linked():
    env = Env(email_user=_user(email_verified=False))
    with pytest.raises(SsoRefusedError) as exc:
        await env.run(_auth(), sso_provider())
    assert exc.value.code == "sso_email_unverified_local"
    env.link_repo.create.assert_not_called()
    env.users.try_create.assert_not_called()


# ---- 5. username race ----


async def test_username_race_retries_next_suffix():
    env = Env()
    created = []

    async def try_create(user):
        created.append(user.username)
        return None if len(created) == 1 else user  # first insert loses the race

    env.users.try_create.side_effect = try_create
    user = await env.run(_auth(username="ruth"), sso_provider())
    assert created == ["ruth", "ruth-2"] and user.username == "ruth-2"


async def test_username_race_bounded():
    env = Env()
    env.users.try_create.side_effect = None
    env.users.try_create.return_value = None
    with pytest.raises(AppError) as exc:
        await env.run(_auth(username="ruth"), sso_provider())
    assert exc.value.status_code == 409
    assert env.users.try_create.await_count == 5


# ---- 6. link to a soft-deleted user ----


async def test_link_to_deleted_user_refused():
    env = Env()
    gone = uuid.uuid4()
    env.link_repo.find_by_provider_and_sub.return_value = MagicMock(user_id=gone)
    env.users.get_by_id.return_value = None
    with pytest.raises(SsoRefusedError) as exc:
        await env.run(_auth(), sso_provider())
    assert exc.value.code == "sso_account_disabled"
    env.tokens.revoke_all_for_user.assert_awaited_once_with(gone)
    env.users.try_create.assert_not_called()
