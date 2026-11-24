"""
@file test_passkeys_roundtrip.py
@brief Real-crypto round trip: soft ES256 authenticator vs PasskeyService (no verify_* mocks).
"""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.config import Settings
from app.core.exceptions import AppError
from app.core.security import create_2fa_pending_token
from app.services.auth.passkeys import PasskeyService
from tests.helpers.webauthn_soft import Auth, b64

S = Settings(SECRET_KEY="pk-test", JWT_ALGORITHM="HS256", APP_BASE_URL="https://home.example:8443")
PR = "app.services.auth.passkeys."


class R:
    """@brief Minimal Valkey stand-in (set / getdel)."""

    def __init__(self) -> None:
        self.d: dict[str, str] = {}

    async def set(self, k: str, v: str, ex: int | None = None) -> None:
        self.d[k] = v

    async def getdel(self, k: str) -> str | None:
        return self.d.pop(k, None)


def mk() -> tuple[PasskeyService, AsyncMock]:
    """@brief Service over an in-memory passkey store."""
    store: dict[bytes, Any] = {}
    repo, users, tokens, audit = AsyncMock(), AsyncMock(), AsyncMock(), AsyncMock()
    repo.session = MagicMock()

    async def add(p: Any) -> Any:
        p.id = uuid.uuid4()
        store[p.credential_id] = p
        return p

    async def get_by_credential(cid: bytes) -> Any:
        return store.get(cid)

    async def list_for_user(uid: uuid.UUID) -> list[Any]:
        return [p for p in store.values() if p.user_id == uid]

    async def touch(p: Any, n: int) -> bool:
        if not (n > p.sign_count or n == p.sign_count == 0):
            return False
        p.sign_count = n
        return True

    repo.add.side_effect = add
    repo.get_by_credential.side_effect = get_by_credential
    repo.list_for_user.side_effect = list_for_user
    repo.touch.side_effect = touch
    cid = uuid.UUID(S.COMMUNITY_ID)
    return PasskeyService(repo, users, tokens, audit, S, cid, "1.2.3.4"), users


def user() -> MagicMock:
    u = MagicMock()
    u.id, u.email, u.is_active, u.display_name = uuid.uuid4(), "a@b.c", True, "A"
    u.community_id, u.memorialized_at = uuid.UUID(S.COMMUNITY_ID), None
    return u


@pytest.fixture
def env():
    r = R()
    ok, fail = AsyncMock(), AsyncMock()
    with (
        patch(PR + "get_pool", return_value=r),
        patch(PR + "assert_password_auth_allowed", AsyncMock()),
        patch(PR + "log_success", ok),
        patch(PR + "log_failure", fail),
        patch(PR + "reserve_attempt", AsyncMock(return_value=True)),
        patch(PR + "clear_user_attempts", AsyncMock()),
        patch(PR + "create_link", AsyncMock()),
        patch(PR + "issue_tokens", AsyncMock(return_value={"access_token": "T"})),
    ):
        svc, users = mk()
        u = user()
        users.get_by_id.return_value = u
        yield svc, u, Auth(), fail


async def _registered(env):
    svc, u, a, fail = env
    pk = await svc.register_verify(u, a.create(await svc.register_options(u)), "Laptop")
    return svc, u, a, fail, pk


async def _bad(coro, code):
    with pytest.raises(AppError) as e:
        await coro
    assert e.value.status_code == 400 and e.value.code == code


async def test_register_and_passwordless_login(env):
    svc, u, a, fail, pk = await _registered(env)
    out = await svc.login_verify(a.get(await svc.login_options(None)), None, None)
    assert out == {"access_token": "T"} and pk.sign_count == 1


async def test_register_wrong_origin_and_replay(env):
    svc, u, a, _ = env
    o = await svc.register_options(u)
    await _bad(
        svc.register_verify(u, Auth().create(o, origin="https://evil"), "x"), "invalid_passkey"
    )
    await _bad(svc.register_verify(u, a.create(o), "x"), "challenge_expired")


async def test_challenge_kind_and_owner_binding(env):
    svc, u, a, _, _ = await _registered(env)
    await _bad(
        svc.login_verify(a.get(await svc.register_options(u)), None, None), "challenge_expired"
    )
    await _bad(
        svc.register_verify(u, Auth().create(await svc.login_options(None)), "x"),
        "challenge_expired",
    )
    await _bad(
        svc.register_verify(u, Auth().create(await svc.register_options(user())), "x"),
        "challenge_expired",
    )


async def test_uv_rules_and_pending_user(env):
    svc, u, a, _, _ = await _registered(env)
    await _bad(
        svc.login_verify(a.get(await svc.login_options(None), uv=False), None, None),
        "invalid_passkey",
    )
    tok = create_2fa_pending_token(u.id, settings=S)
    out = await svc.login_verify(a.get(await svc.login_options(None), uv=False), tok, None)
    assert out["access_token"] == "T"
    other = create_2fa_pending_token(uuid.uuid4(), settings=S)
    await _bad(
        svc.login_verify(a.get(await svc.login_options(None)), other, None), "invalid_passkey"
    )


async def test_wrong_origin_rpid_replay_signature(env):
    svc, u, a, _, _ = await _registered(env)
    await _bad(
        svc.login_verify(a.get(await svc.login_options(None), origin="https://evil"), None, None),
        "invalid_passkey",
    )
    await _bad(
        svc.login_verify(a.get(await svc.login_options(None), rpid="evil.com"), None, None),
        "invalid_passkey",
    )
    c = a.get(await svc.login_options(None))
    await svc.login_verify(c, None, None)
    await _bad(svc.login_verify(c, None, None), "challenge_expired")
    c = a.get(await svc.login_options(None))
    c["response"]["signature"] = b64(b"\x30\x06\x02\x01\x01\x02\x01\x01")
    await _bad(svc.login_verify(c, None, None), "invalid_passkey")


async def test_counter_regression_and_zero_authenticator(env):
    svc, u, a, _, _ = await _registered(env)
    await svc.login_verify(a.get(await svc.login_options(None)), None, None)
    await _bad(
        svc.login_verify(a.get(await svc.login_options(None), count=1), None, None),
        "passkey_cloned",
    )
    await _bad(
        svc.login_verify(a.get(await svc.login_options(None), count=0), None, None),
        "passkey_cloned",
    )
    svc2, users2 = mk()
    u2, z = user(), Auth()
    users2.get_by_id.return_value = u2
    await svc2.register_verify(u2, z.create(await svc2.register_options(u2)), "z")
    out = await svc2.login_verify(z.get(await svc2.login_options(None), count=0), None, None)
    assert out["access_token"] == "T"


async def test_malformed_login_is_400_and_logged(env):
    svc, u, a, fail, _ = await _registered(env)
    for mutate in (
        lambda r: r.pop("authenticatorData"),
        lambda r: r.update(authenticatorData=b64(b"short")),
    ):
        c = a.get(await svc.login_options(None))
        mutate(c["response"])
        fail.reset_mock()
        await _bad(svc.login_verify(c, None, None), "invalid_passkey")
        fail.assert_awaited_once()


async def test_malformed_register_is_400(env):
    svc, u, _, _ = env
    for mutate in (
        lambda r: r.pop("attestationObject"),
        lambda r: r.update(attestationObject=b64(b"\xff\x00")),
    ):
        c = Auth().create(await svc.register_options(u))
        mutate(c["response"])
        await _bad(svc.register_verify(u, c, "x"), "invalid_passkey")


async def test_bad_pending_token_is_logged(env):
    svc, u, a, fail, _ = await _registered(env)
    c = a.get(await svc.login_options(None))
    with pytest.raises(AppError) as e:
        await svc.login_verify(c, "garbage", None)
    assert e.value.status_code == 401
    fail.assert_awaited_once()


async def test_user_handle_must_match_owner(env):
    svc, u, a, fail, _ = await _registered(env)
    c = a.get(await svc.login_options(None))
    c["response"]["userHandle"] = b64(uuid.uuid4().bytes)
    await _bad(svc.login_verify(c, None, None), "invalid_passkey")
    c = a.get(await svc.login_options(None))
    c["response"]["userHandle"] = b64(u.id.bytes)
    assert (await svc.login_verify(c, None, None))["access_token"] == "T"
