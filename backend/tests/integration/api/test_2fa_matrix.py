"""
@file test_2fa_matrix.py
@brief Real-Postgres + Valkey matrix: every login path demands the required second factor.

{password, magic_link} x {no 2FA, TOTP, passkey}, recovery codes, SSO, and the
community ``require_2fa`` policy after the 7-day grace period.
"""

from __future__ import annotations

import json
import os
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import patch

import pyotp
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.core import valkey
from app.core.dependencies import get_db
from app.core.security import hash_password, hash_token
from app.core.valkey import DB_CACHE, close_pools, get_pool
from app.models.auth import MagicLinkToken, UserBackupCode
from app.models.community import Community
from app.models.passkey import Passkey
from app.models.user import User
from app.services.auth.two_factor import seal_secret
from tests.helpers.webauthn_soft import Auth

DB_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://nexara:nexara@localhost:5432/nexara_test"
)
PW = "Correct-Horse-Battery-42"
ORIGIN = "http://localhost:8000"


@pytest.fixture
async def factory():
    """@brief Sessions on one connection inside a transaction rolled back after the test."""
    engine = create_async_engine(DB_URL, echo=False)
    async with engine.connect() as conn:
        trans = await conn.begin()
        yield async_sessionmaker(
            bind=conn,
            class_=AsyncSession,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        await trans.rollback()
    await engine.dispose()


@pytest.fixture
async def client(test_app, factory):
    """@brief HTTP client whose requests use the rolled-back test connection."""

    async def _db():
        async with factory() as s:
            try:
                yield s
                await s.commit()
            except Exception:
                await s.rollback()
                raise

    test_app.dependency_overrides[get_db] = _db
    valkey._pools.clear()  # pools are bound to the loop that created them
    with patch("app.services.auth.signin_log.async_session_factory", factory):
        # Route limits live in shared Valkey keyed by client IP: use a private bucket.
        ip = {"X-Forwarded-For": f"198.18.{secrets.randbelow(256)}.{secrets.randbelow(256)}"}
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url=ORIGIN, headers=ip) as c:
            yield c
    test_app.dependency_overrides.clear()
    await close_pools()


def _settings():
    from tests.integration.conftest import _TEST_SETTINGS

    return _TEST_SETTINGS


async def _user(
    factory,
    *,
    totp: bool = False,
    passkey: bool = False,
    password: bool = True,
    since: datetime | None = None,
) -> dict[str, Any]:
    """@brief Insert a member with the requested factors; returns handles for the test."""
    tag = uuid.uuid4().hex[:10]
    out: dict[str, Any] = {"email": f"mx_{tag}@nexara.dev"}
    cid = uuid.UUID(_settings().COMMUNITY_ID)
    async with factory() as s:
        u = User(
            community_id=cid,
            email=out["email"],
            username=f"mx_{tag}",
            display_name="Matrix",
            password_hash=hash_password(PW) if password else None,
            is_active=True,
            two_factor_required_since=since,
        )
        if totp:
            out["secret"] = pyotp.random_base32()
            u.totp_secret = seal_secret(out["secret"], _settings())
            u.totp_enabled = True
        s.add(u)
        await s.flush()
        if totp:
            out["codes"] = [secrets.token_hex(4).upper() for _ in range(3)]
            s.add_all(UserBackupCode(user_id=u.id, code_hash=hash_token(c)) for c in out["codes"])
        if passkey:
            a = Auth(rpid="localhost")
            out["auth"] = a
            s.add(
                Passkey(
                    user_id=u.id,
                    community_id=cid,
                    credential_id=a.cid,
                    public_key=a.cose(),
                    sign_count=0,
                    transports=["internal"],
                    name="Key",
                )
            )
        await s.commit()
        out["id"] = u.id
    return out


async def _start(c: AsyncClient, factory, mode: str, u: dict[str, Any]):
    """@brief First login step via password or magic link."""
    if mode == "password":
        return await c.post("/api/v1/auth/login", json={"email": u["email"], "password": PW})
    raw = str(uuid.uuid4())
    async with factory() as s:
        s.add(
            MagicLinkToken(
                user_id=u["id"],
                token_hash=hash_token(raw),
                expires_at=datetime.now(UTC) + timedelta(minutes=15),
            )
        )
        await s.commit()
    return await c.get("/api/v1/auth/magic-link/verify", params={"token": raw})


async def _passkey(c: AsyncClient, u: dict[str, Any], pending: str | None):
    opts = (await c.post("/api/v1/auth/passkeys/login/options", json={"email": u["email"]})).json()
    cred = u["auth"].get(opts, origin=ORIGIN)
    return await c.post(
        "/api/v1/auth/passkeys/login/verify", json={"credential": cred, "pending_token": pending}
    )


def _pending(r) -> dict[str, Any]:
    body = r.json()
    assert r.status_code == 200, body
    assert body["requires_2fa"] is True and body["access_token"] is None
    return body


@pytest.mark.parametrize("mode", ["password", "magic_link"])
async def test_no_second_factor_gets_tokens(client, factory, mode):
    u = await _user(factory)
    r = await _start(client, factory, mode, u)
    assert r.status_code == 200 and r.json()["access_token"]
    assert r.json()["requires_2fa"] is False


@pytest.mark.parametrize("mode", ["password", "magic_link"])
async def test_totp_required(client, factory, mode):
    u = await _user(factory, totp=True)
    body = _pending(await _start(client, factory, mode, u))
    assert body["two_factor_methods"] == ["totp", "recovery"]
    tok = body["two_factor_token"]
    hdr = {"Authorization": f"Bearer {tok}"}
    assert (await client.get("/api/v1/users/me", headers=hdr)).status_code == 401
    bad = await client.post(
        "/api/v1/auth/2fa/login", json={"two_factor_token": tok, "code": "000000"}
    )
    assert bad.status_code == 401
    code = pyotp.TOTP(u["secret"]).now()
    ok = await client.post("/api/v1/auth/2fa/login", json={"two_factor_token": tok, "code": code})
    assert ok.status_code == 200 and ok.json()["access_token"]


@pytest.mark.parametrize("mode", ["password", "magic_link"])
async def test_passkey_required(client, factory, mode):
    u = await _user(factory, passkey=True)
    body = _pending(await _start(client, factory, mode, u))
    assert body["two_factor_methods"] == ["passkey"]
    tok = body["two_factor_token"]
    no_totp = await client.post(
        "/api/v1/auth/2fa/login", json={"two_factor_token": tok, "code": "123456"}
    )
    assert no_totp.status_code == 401
    ok = await _passkey(client, u, tok)
    assert ok.status_code == 200, ok.json()
    assert ok.json()["access_token"]


async def test_totp_and_passkey_offers_both(client, factory):
    u = await _user(factory, totp=True, passkey=True)
    body = _pending(await _start(client, factory, "password", u))
    assert body["two_factor_methods"] == ["totp", "recovery", "passkey"]
    ok = await _passkey(client, u, body["two_factor_token"])
    assert ok.status_code == 200 and ok.json()["access_token"]


async def test_recovery_code_works_once(client, factory):
    u = await _user(factory, totp=True)
    code = u["codes"][0]
    for expected in (200, 401):
        tok = _pending(await _start(client, factory, "password", u))["two_factor_token"]
        r = await client.post(
            "/api/v1/auth/2fa/login", json={"two_factor_token": tok, "code": code}
        )
        assert r.status_code == expected


async def _sso(client: AsyncClient, user_id: uuid.UUID):
    code = secrets.token_urlsafe(16)
    payload = json.dumps({"user_id": str(user_id), "provider_slug": "x"})
    await get_pool(_settings(), DB_CACHE).setex(f"oauth_exchange:{code}", 60, payload)
    return await client.post("/api/v1/oauth/exchange", json={"code": code})


async def test_sso_with_totp_gets_tokens_directly(client, factory):
    u = await _user(factory, totp=True, passkey=True)
    r = await _sso(client, u["id"])
    assert r.status_code == 200, r.json()
    assert r.json()["access_token"] and not r.json()["requires_2fa"]


async def _policy(factory, value: str) -> None:
    async with factory() as s:
        cid = uuid.UUID(_settings().COMMUNITY_ID)
        await s.execute(update(Community).where(Community.id == cid).values(require_2fa=value))
        await s.commit()


async def _access(r) -> dict[str, str]:
    assert r.status_code == 200, r.json()
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_policy_everyone_day8_blocks_until_enrolled(client, factory):
    await _policy(factory, "everyone")
    u = await _user(factory, since=datetime.now(UTC) - timedelta(days=8))
    h = await _access(await _start(client, factory, "password", u))
    r = await client.get("/api/v1/posts", headers=h)
    assert r.status_code == 403 and r.json()["error"]["code"] == "2fa_setup_required"
    assert (await client.get("/api/v1/auth/2fa/status", headers=h)).status_code == 200
    assert (await client.get("/api/v1/users/me", headers=h)).status_code == 200
    media = await client.get(f"/api/v1/media/{uuid.uuid4()}/file", headers=h)
    assert media.status_code == 403 and media.json()["error"]["code"] == "2fa_setup_required"
    thumb = await client.get(f"/api/v1/media/{uuid.uuid4()}/thumbnail", headers=h)
    assert thumb.status_code == 403
    assert (await client.post("/api/v1/auth/logout", headers=h)).status_code == 200
    assert (await client.post("/api/v1/auth/passkeys/register/options", headers=h)).status_code == (
        200
    )


async def test_policy_within_grace_allows(client, factory):
    await _policy(factory, "everyone")
    u = await _user(factory, since=datetime.now(UTC) - timedelta(days=2))
    h = await _access(await _start(client, factory, "password", u))
    assert (await client.get("/api/v1/posts", headers=h)).status_code == 200


async def test_policy_never_applies_to_sso_only(client, factory):
    await _policy(factory, "everyone")
    u = await _user(factory, password=False, since=datetime.now(UTC) - timedelta(days=8))
    h = await _access(await _sso(client, u["id"]))
    assert (await client.get("/api/v1/posts", headers=h)).status_code == 200


async def test_policy_satisfied_by_factor(client, factory):
    await _policy(factory, "everyone")
    u = await _user(factory, totp=True, since=datetime.now(UTC) - timedelta(days=8))
    tok = _pending(await _start(client, factory, "password", u))["two_factor_token"]
    code = pyotp.TOTP(u["secret"]).now()
    r = await client.post("/api/v1/auth/2fa/login", json={"two_factor_token": tok, "code": code})
    assert (await client.get("/api/v1/posts", headers=await _access(r))).status_code == 200
