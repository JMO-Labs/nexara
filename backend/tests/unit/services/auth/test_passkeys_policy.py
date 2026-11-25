"""
@file test_passkeys_policy.py
@brief Passwordless passkey vs SSO-only mode / SSO-only users; 2FA-step allowCredentials.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import AppError, AuthorizationError
from app.core.security import create_2fa_pending_token
from tests.helpers.webauthn_soft import Auth
from tests.unit.services.auth.test_passkeys_roundtrip import PR, R, S, mk, user


@pytest.fixture
def env():
    fail = AsyncMock()
    sso = AsyncMock()
    with (
        patch(PR + "get_pool", return_value=R()),
        patch(PR + "assert_password_auth_allowed", sso),
        patch(PR + "log_success", AsyncMock()),
        patch(PR + "log_failure", fail),
        patch(PR + "reserve_attempt", AsyncMock(return_value=True)),
        patch(PR + "finish_pending", AsyncMock()),
        patch(PR + "create_link", AsyncMock()),
        patch(PR + "issue_tokens", AsyncMock(return_value={"access_token": "T"})),
    ):
        svc, users = mk()
        u = user()
        users.get_by_id.return_value = u
        yield svc, u, Auth(), fail, sso


async def _reg(env):
    svc, u, a, *_ = env
    await svc.register_verify(u, a.create(await svc.register_options(u)), "Key")


async def test_sso_only_mode_blocks_passwordless(env):
    svc, u, a, fail, sso = env
    await _reg(env)
    sso.side_effect = AuthorizationError(message="sso only")
    with pytest.raises(AppError) as e:
        await svc.login_verify(a.get(await svc.login_options(None)), None, None)
    assert e.value.status_code == 403
    assert fail.await_args.args[4] == "sso_only"


async def test_sso_only_mode_allows_passkey_as_second_factor(env):
    svc, u, a, _, sso = env
    await _reg(env)
    sso.side_effect = AuthorizationError(message="sso only")
    held = {"provider_id": str(uuid.uuid4()), "sub": "s"}
    tok = create_2fa_pending_token(u.id, settings=S, oauth_link=held)
    with patch(PR + "create_link", AsyncMock()) as link:
        out = await svc.login_verify(a.get(await svc.login_options(None)), tok, None)
    assert out["access_token"] == "T"
    sso.assert_not_awaited()
    # A held first SSO link is created only once the passkey 2FA step passes.
    assert link.await_args.args[1:] == (u.id, held)


async def test_sso_user_cannot_sign_in_passwordless(env):
    svc, u, a, fail, _ = env
    u.password_hash = None
    await _reg(env)
    with pytest.raises(AppError) as e:
        await svc.login_verify(a.get(await svc.login_options(None)), None, None)
    assert e.value.status_code == 403 and e.value.code == "sso_login_required"
    assert fail.await_args.args[4] == "sso_user"


async def test_pending_token_fills_allow_credentials(env):
    svc, u, a, *_ = env
    await _reg(env)
    tok = create_2fa_pending_token(u.id, settings=S)
    opts = await svc.login_options(None, tok)
    assert len(opts["allowCredentials"]) == 1
    assert (await svc.login_options(None, "junk"))["allowCredentials"] == []
    svc._users.get_by_id.return_value = None
    other = create_2fa_pending_token(uuid.uuid4(), settings=S)
    assert (await svc.login_options(None, other))["allowCredentials"] == []
