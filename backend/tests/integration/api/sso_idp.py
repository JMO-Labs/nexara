"""
@file sso_idp.py
@brief Shared real-Postgres + Valkey SSO fixtures and a stubbed OIDC IdP.

The IdP (discovery, token, JWKS, userinfo) is an ``httpx.MockTransport`` with a
real RSA signer, so ID tokens are verified exactly as in production. The DB,
Valkey, cookies and every route run for real.
"""

from __future__ import annotations

import os
import secrets
import time
import uuid
from contextlib import contextmanager
from http.cookies import SimpleCookie
from typing import Any
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from authlib.jose import JsonWebKey, JsonWebToken
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.core import valkey
from app.core.dependencies import get_db
from app.core.security import create_access_token
from app.core.valkey import close_pools
from app.models.signin_event import SigninEvent
from app.models.user import User
from app.services.oauth import discovery, token_verifier

DB_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://nexara:nexara@localhost:5432/nexara_test"
)
ORIGIN = "http://localhost:8000"
_REAL_CLIENT = httpx.AsyncClient


def settings():
    """@brief The integration test settings."""
    from tests.integration.conftest import _TEST_SETTINGS

    return _TEST_SETTINGS


CID = uuid.UUID(settings().COMMUNITY_ID)


@pytest.fixture(name="factory")
async def factory_fixture():
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


@pytest.fixture(name="client")
async def client_fixture(test_app, factory):
    """@brief HTTP client on the rolled-back connection (failed sign-ins included)."""

    async def _db():
        async with factory() as s:
            try:
                yield s
                await s.commit()
            except Exception:
                await s.rollback()
                raise

    test_app.dependency_overrides[get_db] = _db
    valkey._pools.clear()
    discovery.clear_cache()
    token_verifier._JWKS_CACHE.clear()
    ip = {"X-Forwarded-For": f"198.18.{secrets.randbelow(256)}.{secrets.randbelow(256)}"}
    with patch("app.services.auth.signin_log.async_session_factory", factory):
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url=ORIGIN, headers=ip
        ) as c:
            yield c
    test_app.dependency_overrides.clear()
    await close_pools()


async def admin_headers(factory) -> dict[str, str]:
    """@brief Insert an admin; returns bearer headers."""
    tag = uuid.uuid4().hex[:10]
    async with factory() as s:
        u = User(
            community_id=CID,
            email=f"adm_{tag}@nexara.dev",
            username=f"adm_{tag}",
            display_name="Admin",
            role="admin",
            is_active=True,
            email_verified=True,
        )
        s.add(u)
        await s.commit()
    return {"Authorization": f"Bearer {create_access_token(u.id, settings=settings())}"}


async def count(factory, stmt) -> int:
    """@brief Scalar count."""
    async with factory() as s:
        return int((await s.execute(stmt)).scalar_one())


def sso_failures(reason: str | None = None):
    """@brief Count statement for failed SSO sign-in rows (optionally by reason)."""
    stmt = select(func.count()).where(SigninEvent.method == "sso", SigninEvent.success.is_(False))
    return stmt.where(SigninEvent.reason == reason) if reason else stmt


class StubIdP:
    """
    @brief In-process OIDC provider: discovery, token, JWKS, userinfo.

    Set ``claims`` before the callback; ``token_status`` / ``userinfo_status``
    / ``id_token`` toggle failure modes.
    """

    def __init__(self) -> None:
        self.host = f"idp-{uuid.uuid4().hex[:8]}.example.com"
        self.issuer = f"https://{self.host}/app"
        self.discovery_url = f"{self.issuer}/.well-known/openid-configuration"
        self._key = JsonWebKey.generate_key("RSA", 2048, is_private=True)
        self.claims: dict[str, Any] = {}
        self.nonce: str | None = None
        self.token_status = 200
        self.userinfo_status = 200
        self.id_token = True

    def _sign(self) -> str:
        now = int(time.time())
        payload = {"iss": self.issuer, "aud": "nexara", "iat": now, "exp": now + 300,
                   "nonce": self.nonce, **self.claims}  # fmt: skip
        header = {"alg": "RS256", "kid": self._key.as_dict()["kid"]}
        return JsonWebToken(["RS256"]).encode(header, payload, self._key).decode()

    def handle(self, request: httpx.Request) -> httpx.Response:
        """@brief Route one IdP request."""
        path = request.url.path
        if path.endswith("/.well-known/openid-configuration"):
            return httpx.Response(200, json={
                "issuer": self.issuer,
                "authorization_endpoint": f"{self.issuer}/authorize",
                "token_endpoint": f"{self.issuer}/token",
                "userinfo_endpoint": f"{self.issuer}/userinfo",
                "jwks_uri": f"{self.issuer}/jwks",
            })  # fmt: skip
        if path.endswith("/jwks"):
            return httpx.Response(200, json={"keys": [self._key.as_dict(is_private=False)]})
        if path.endswith("/token"):
            if self.token_status != 200:
                return httpx.Response(self.token_status, json={"error": "invalid_grant"})
            body: dict[str, Any] = {"access_token": "at", "token_type": "Bearer"}
            if self.id_token:
                body["id_token"] = self._sign()
            return httpx.Response(200, json=body)
        if path.endswith("/userinfo"):
            return httpx.Response(self.userinfo_status, json=self.claims)
        return httpx.Response(404)

    @contextmanager
    def serving(self):
        """@brief Route every outbound httpx.AsyncClient call to this IdP."""

        def make(*args: Any, **kwargs: Any) -> httpx.AsyncClient:
            kwargs["transport"] = httpx.MockTransport(self.handle)
            return _REAL_CLIENT(*args, **kwargs)

        with patch("httpx.AsyncClient", make):
            yield self


def provider_body(idp: StubIdP, slug: str, **over: Any) -> dict[str, Any]:
    """@brief Admin create payload for an authentik-preset provider at ``idp``."""
    return {
        "slug": slug,
        "display_name": "Authentik",
        "provider_type": "oidc",
        "client_id": "nexara",
        "client_secret": "s3cret",
        "discovery_url": idp.discovery_url,
        "preset": "authentik",
        "claim_mapping": {"groups": "groups"},
        **over,
    }


async def start_login(client, slug: str) -> tuple[str, dict[str, str], httpx.Response]:
    """@brief GET /oauth/{slug}/login; returns state, login cookies, response."""
    r = await client.get(f"/api/v1/oauth/{slug}/login", follow_redirects=False)
    if r.status_code != 302 or "state=" not in r.headers["location"]:
        return "", {}, r
    query = parse_qs(urlsplit(r.headers["location"]).query)
    jar: SimpleCookie = SimpleCookie()
    for raw in r.headers.get_list("set-cookie"):
        jar.load(raw)
    cookies = {k: v.value for k, v in jar.items()}
    cookies["_nonce"] = query.get("nonce", [""])[0]
    return query["state"][0], cookies, r


async def sso_login(client, idp: StubIdP, slug: str, claims: dict[str, Any]) -> httpx.Response:
    """@brief login -> IdP -> callback; returns the callback response."""
    state, cookies, _r = await start_login(client, slug)
    idp.nonce, idp.claims = cookies.pop("_nonce", None), claims
    return await client.get(
        f"/api/v1/oauth/{slug}/callback",
        params={"code": "c0de", "state": state},
        cookies=cookies,
        follow_redirects=False,
    )


def failed(resp: httpx.Response) -> bool:
    """@brief Sent to /login?error=sso_failed (never raw JSON)."""
    return resp.status_code == 302 and resp.headers["location"].endswith("/login?error=sso_failed")
