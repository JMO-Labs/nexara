"""
@file test_policy.py
@brief Unit tests for the second-factor policy (claims + grace enforcement).
"""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import AppError
from app.services.auth import policy

P = "app.services.auth.policy."
PAST = {"twofa_setup_required": True, "grace_until": int(time.time()) - 1}


def _user(**kw):
    base = dict(
        id=uuid.uuid4(),
        community_id=uuid.uuid4(),
        role="member",
        password_hash="h",
        totp_enabled=False,
        two_factor_required_since=None,
    )
    return SimpleNamespace(**{**base, **kw})


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/posts",
        "/api/v1/sse",
        "/ws",
        "/api/v1/users/me/password",
        "/api/v1/auth/passkeys/1234",
    ],
)
def test_blocks_outside_allowlist(path):
    with pytest.raises(AppError) as e:
        policy.enforce_setup(PAST, path)
    assert e.value.status_code == 403 and e.value.code == "2fa_setup_required"


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/auth/2fa/status",
        "/api/v1/auth/2fa/totp/start",
        "/api/v1/auth/passkeys/register/options",
        "/api/v1/users/me",
        "/api/v1/auth/logout",
        "/api/v1/auth/passkeys",
    ],
)
def test_allowlist_passes(path):
    policy.enforce_setup(PAST, path)


def test_within_grace_or_no_claim_passes():
    future = {"twofa_setup_required": True, "grace_until": int(time.time()) + 60}
    policy.enforce_setup(future, "/api/v1/posts")
    policy.enforce_setup({}, "/api/v1/posts")


async def _claims(user, pol: str, methods: list[str]):
    repo = AsyncMock()
    repo.get_policy.return_value = pol
    with (
        patch(P + "TwoFactorRepository", return_value=repo),
        patch(P + "factor_methods", AsyncMock(return_value=methods)),
    ):
        return await policy.setup_claims(AsyncMock(), user)


async def test_claims_cover_member_without_factor_and_start_clock():
    u = _user()
    out = await _claims(u, "everyone", [])
    assert out["twofa_setup_required"] is True
    assert u.two_factor_required_since is not None
    assert out["grace_until"] == int((u.two_factor_required_since + policy.GRACE).timestamp())


async def test_claims_keep_existing_clock():
    since = datetime.now(UTC) - timedelta(days=8)
    out = await _claims(_user(two_factor_required_since=since), "everyone", [])
    assert out["grace_until"] == int((since + timedelta(days=7)).timestamp())


@pytest.mark.parametrize(
    ("kw", "pol", "methods"),
    [
        ({}, "off", []),
        ({}, "admins", []),
        ({"password_hash": None}, "everyone", []),
        ({}, "everyone", ["passkey"]),
    ],
)
async def test_claims_empty_when_not_covered(kw, pol, methods):
    assert await _claims(_user(**kw), pol, methods) == {}


async def test_admins_policy_covers_admin():
    assert await _claims(_user(role="admin"), "admins", [])


async def test_factor_methods_shapes():
    repo = AsyncMock()
    repo.count_for_user.return_value = 2
    with patch(P + "PasskeyRepository", return_value=repo):
        assert await policy.factor_methods(AsyncMock(), _user(totp_enabled=True)) == [
            "totp",
            "recovery",
            "passkey",
        ]
        repo.count_for_user.return_value = 0
        assert await policy.factor_methods(AsyncMock(), _user()) == []
        assert not await policy.second_factor_needed(AsyncMock(), _user())
