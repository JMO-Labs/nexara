"""
@file test_sso_test_login.py
@brief Real-Postgres + Valkey: admin SSO test login reports and never provisions.

The IdP is mocked at the token exchange and ID-token verification; state, Valkey
keys, the callback and the DB are real.
"""

from __future__ import annotations

import os
import secrets
import uuid
from typing import Any
from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qs, urlsplit

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.core import valkey
from app.core.dependencies import get_db
from app.core.security import create_access_token
from app.core.valkey import DB_CACHE, close_pools, get_pool
from app.models.auth import RefreshToken
from app.models.oauth_provider import OAuthProvider
from app.models.signin_event import SigninEvent
from app.models.subgroup import Subgroup
from app.models.user import User
from app.models.user_oauth_link import UserOAuthLink
from app.services.oauth.flow import OAuthFlow

DB_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://nexara:nexara@localhost:5432/nexara_test"
)
ORIGIN = "http://localhost:8000"


def _settings():
    from tests.integration.conftest import _TEST_SETTINGS

    return _TEST_SETTINGS


CID = uuid.UUID(_settings().COMMUNITY_ID)


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
    valkey._pools.clear()
    ip = {"X-Forwarded-For": f"198.18.{secrets.randbelow(256)}.{secrets.randbelow(256)}"}
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url=ORIGIN, headers=ip) as c:
        yield c
    test_app.dependency_overrides.clear()
    await close_pools()


async def _user(factory, role: str) -> dict[str, str]:
    """@brief Insert a user; returns bearer headers."""
    tag = uuid.uuid4().hex[:10]
    async with factory() as s:
        u = User(
            community_id=CID,
            email=f"st_{tag}@nexara.dev",
            username=f"st_{tag}",
            display_name="Tester",
            role=role,
            is_active=True,
            email_verified=True,
        )
        s.add(u)
        await s.commit()
        token = create_access_token(u.id, settings=_settings())
    return {"Authorization": f"Bearer {token}"}


async def _provider(factory, **over: Any) -> OAuthProvider:
    async with factory() as s:
        sub = Subgroup(community_id=CID, name="Smith Family", slug=f"smith-{uuid.uuid4().hex[:6]}")
        s.add(sub)
        await s.flush()
        p = OAuthProvider(
            community_id=CID,
            slug=f"t{uuid.uuid4().hex[:8]}",
            display_name="Test IdP",
            provider_type="oidc",
            client_id="c",
            client_secret_encrypted="x",
            authorization_endpoint="https://idp.example.com/authorize",
            token_endpoint="https://idp.example.com/token",
            enabled=False,  # testing works before the provider is enabled
            claim_mapping={
                "groups": "groups",
                "group_mapping": {"smiths": [{"subgroup_id": str(sub.id), "role": "member"}]},
            },
            **over,
        )
        s.add(p)
        await s.commit()
        return p


async def _count(factory, stmt) -> int:
    async with factory() as s:
        return int((await s.execute(stmt)).scalar_one())


async def _run_test_login(client, factory, admin, provider, claims) -> Any:
    """@brief Start, then hit the callback as the IdP would (no login cookies)."""
    r = await client.post(f"/api/v1/admin/oauth/providers/{provider.id}/test-login", headers=admin)
    assert r.status_code == 200, r.text
    state = parse_qs(urlsplit(r.json()["authorize_url"]).query)["state"][0]
    with (
        patch.object(OAuthFlow, "exchange_code", AsyncMock(return_value={"id_token": "t"})),
        patch("app.api.v1.oauth.verify_id_token", AsyncMock(return_value=claims)),
    ):
        return await client.get(
            f"/api/v1/oauth/{provider.slug}/callback?code=c&state={state}",
            follow_redirects=False,
        )


def _claims(email: str) -> dict[str, Any]:
    return {"sub": f"idp-{uuid.uuid4().hex}", "email": email, "email_verified": True,
            "name": "New Person", "groups": ["smiths"]}  # fmt: skip


async def test_test_login_reports_without_provisioning(client, factory):
    admin = await _user(factory, "admin")
    provider = await _provider(factory)
    email = f"new_{uuid.uuid4().hex[:8]}@example.com"
    tokens_before = await _count(factory, select(func.count()).select_from(RefreshToken))
    signins_before = await _count(factory, select(func.count()).select_from(SigninEvent))
    cache = get_pool(_settings(), DB_CACHE)
    exchanges_before = len(await cache.keys("oauth_exchange:*"))

    resp = await _run_test_login(client, factory, admin, provider, _claims(email))

    assert resp.status_code == 302
    loc = urlsplit(resp.headers["location"])
    assert loc.path == "/sso-test"
    assert "set-cookie" not in resp.headers
    result_id = parse_qs(loc.query)["result"][0]
    assert await _count(factory, select(func.count()).where(User.email == email)) == 0
    links = select(func.count()).where(UserOAuthLink.provider_id == provider.id)
    assert await _count(factory, links) == 0
    assert await _count(factory, select(func.count()).select_from(RefreshToken)) == tokens_before
    assert await _count(factory, select(func.count()).select_from(SigninEvent)) == signins_before
    assert len(await cache.keys("oauth_exchange:*")) == exchanges_before

    r = await client.get(f"/api/v1/admin/oauth/test-login/{result_id}", headers=admin)
    assert r.status_code == 200
    body = r.json()
    assert body["claims"]["email"] == email
    assert body["identity"]["groups"] == ["smiths"]
    assert body["role"] == "member"
    assert [s["name"] for s in body["subgroups"]] == ["Smith Family"]
    assert body["outcome"] == {"allowed": True, "action": "create", "code": None}


async def test_result_is_single_use_and_owner_only(client, factory):
    admin = await _user(factory, "admin")
    other_admin = await _user(factory, "admin")
    provider = await _provider(factory)
    resp = await _run_test_login(client, factory, admin, provider, _claims("x@example.com"))
    result_id = parse_qs(urlsplit(resp.headers["location"]).query)["result"][0]

    url = f"/api/v1/admin/oauth/test-login/{result_id}"
    assert (await client.get(url, headers=other_admin)).status_code == 404
    # A foreign read burns the result: it is never readable twice.
    assert (await client.get(url, headers=admin)).status_code == 404


async def test_result_second_read_404(client, factory):
    admin = await _user(factory, "admin")
    provider = await _provider(factory)
    resp = await _run_test_login(client, factory, admin, provider, _claims("y@example.com"))
    result_id = parse_qs(urlsplit(resp.headers["location"]).query)["result"][0]
    url = f"/api/v1/admin/oauth/test-login/{result_id}"
    assert (await client.get(url, headers=admin)).status_code == 200
    assert (await client.get(url, headers=admin)).status_code == 404


async def test_gate_refusal_reported(client, factory):
    admin = await _user(factory, "admin")
    provider = await _provider(factory, allowed_domains=["corp.example"], auto_create_users=True)
    resp = await _run_test_login(client, factory, admin, provider, _claims("z@example.com"))
    result_id = parse_qs(urlsplit(resp.headers["location"]).query)["result"][0]
    body = (await client.get(f"/api/v1/admin/oauth/test-login/{result_id}", headers=admin)).json()
    assert body["outcome"] == {"allowed": False, "action": None, "code": "sso_domain_not_allowed"}


async def test_non_admin_cannot_start_test_login(client, factory):
    member = await _user(factory, "member")
    provider = await _provider(factory)
    before = len(await get_pool(_settings(), DB_CACHE).keys("oauth_test:*"))
    r = await client.post(f"/api/v1/admin/oauth/providers/{provider.id}/test-login", headers=member)
    assert r.status_code == 403
    assert len(await get_pool(_settings(), DB_CACHE).keys("oauth_test:*")) == before


async def test_unknown_state_still_rejected(client, factory):
    provider = await _provider(factory)
    r = await client.get(f"/api/v1/oauth/{provider.slug}/callback?code=c&state=nope")
    assert r.status_code == 401
