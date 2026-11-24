"""
@file test_sso_e2e.py
@brief End-to-end SSO on real Postgres + Valkey with a stubbed OIDC IdP.

login -> IdP -> callback -> /callback?code= -> POST /oauth/exchange -> tokens,
plus provider re-create / disable (no stale provider on any worker) and slug reuse.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from urllib.parse import parse_qs, urlsplit

from sqlalchemy import func, select

from app.models.signin_event import SigninEvent
from app.models.user import User
from app.models.user_oauth_link import UserOAuthLink
from tests.integration.api.sso_idp import (
    CID,
    StubIdP,
    admin_headers,
    client_fixture,  # noqa: F401
    count,
    factory_fixture,  # noqa: F401
    failed,
    provider_body,
    sso_login,
)


def _claims(email: str, sub: str | None = None, **extra) -> dict:
    # authentik's default email scope sends email_verified=false (L3).
    return {"sub": sub or f"ak-{uuid.uuid4().hex}", "email": email, "email_verified": False,
            "name": "Ada Lovelace", "preferred_username": "ada", **extra}  # fmt: skip


async def _create(client, admin, idp, slug, **over):
    return await client.post(
        "/api/v1/admin/oauth/providers", json=provider_body(idp, slug, **over), headers=admin
    )


async def test_full_sso_login_issues_tokens_and_records_signin(client, factory):
    admin = await admin_headers(factory)
    idp, slug = StubIdP(), f"ak{uuid.uuid4().hex[:6]}"
    email = f"ada_{uuid.uuid4().hex[:8]}@example.com"
    with idp.serving():
        r = await _create(client, admin, idp, slug)
        assert r.status_code == 201, r.text
        assert r.json()["trust_email"] is True  # authentik preset default
        provider_id = uuid.UUID(r.json()["id"])

        cb = await sso_login(client, idp, slug, _claims(email))

    assert cb.status_code == 302, cb.text
    loc = urlsplit(cb.headers["location"])
    assert loc.path == "/callback"  # L1: app/(auth)/callback, not /auth/callback
    code = parse_qs(loc.query)["code"][0]

    ex = await client.post("/api/v1/oauth/exchange", json={"code": code})
    assert ex.status_code == 200, ex.text
    assert ex.json()["access_token"]
    assert "refresh_token=" in ex.headers.get("set-cookie", "")
    # Single use (atomic GETDEL).
    assert (await client.post("/api/v1/oauth/exchange", json={"code": code})).status_code == 401

    async with factory() as s:
        user = (await s.execute(select(User).where(User.email == email))).scalar_one()
        link = (
            await s.execute(select(UserOAuthLink).where(UserOAuthLink.user_id == user.id))
        ).scalar_one()
    assert link.provider_id == provider_id
    ok = select(func.count()).where(
        SigninEvent.user_id == user.id, SigninEvent.method == "sso", SigninEvent.success.is_(True)
    )
    assert await count(factory, ok) == 1


async def test_recreated_slug_links_to_new_provider(client, factory):
    """L2 + L5: delete, re-create the same slug -> 201 and the link uses the new id."""
    admin = await admin_headers(factory)
    idp, slug = StubIdP(), f"ak{uuid.uuid4().hex[:6]}"
    email = f"bob_{uuid.uuid4().hex[:8]}@example.com"
    sub = f"ak-{uuid.uuid4().hex}"
    with idp.serving():
        first = (await _create(client, admin, idp, slug)).json()
        assert (await sso_login(client, idp, slug, _claims(email, sub))).status_code == 302
        r = await client.delete(f"/api/v1/admin/oauth/providers/{first['id']}", headers=admin)
        assert r.status_code == 200
        second = await _create(client, admin, idp, slug)
        assert second.status_code == 201, second.text
        new_id = uuid.UUID(second.json()["id"])

        cb = await sso_login(client, idp, slug, _claims(email, sub))
    assert urlsplit(cb.headers["location"]).path == "/callback", cb.headers["location"]
    links = select(UserOAuthLink.provider_id).where(UserOAuthLink.sub == sub)
    async with factory() as s:
        ids = set((await s.execute(links)).scalars().all())
    assert new_id in ids and uuid.UUID(first["id"]) != new_id


async def test_disabled_provider_refused_immediately(client, factory):
    admin = await admin_headers(factory)
    idp, slug = StubIdP(), f"ak{uuid.uuid4().hex[:6]}"
    with idp.serving():
        pid = (await _create(client, admin, idp, slug)).json()["id"]
        r = await client.post(f"/api/v1/admin/oauth/providers/{pid}/toggle", headers=admin)
        assert r.json()["enabled"] is False
        login = await client.get(f"/api/v1/oauth/{slug}/login", follow_redirects=False)
        assert failed(login)
        # A login already in flight is refused at the callback too.
        cb = await sso_login(client, idp, slug, _claims("x@example.com"))
    assert failed(cb)


async def test_live_duplicate_slug_is_409(client, factory):
    admin = await admin_headers(factory)
    idp, slug = StubIdP(), f"ak{uuid.uuid4().hex[:6]}"
    with idp.serving():
        assert (await _create(client, admin, idp, slug)).status_code == 201
        dup = await _create(client, admin, idp, slug)
    assert dup.status_code == 409
    assert dup.json()["error"]["code"] == "sso_slug_taken"


async def test_trust_email_off_refuses_unverified(client, factory):
    admin = await admin_headers(factory)
    idp, slug = StubIdP(), f"ak{uuid.uuid4().hex[:6]}"
    email = f"u_{uuid.uuid4().hex[:8]}@example.com"
    with idp.serving():
        r = await _create(client, admin, idp, slug, trust_email=False)
        assert r.json()["trust_email"] is False
        cb = await sso_login(client, idp, slug, _claims(email))
    query = parse_qs(urlsplit(cb.headers["location"]).query)
    assert query["error"] == ["sso_email_unverified"]
    assert await count(factory, select(func.count()).where(User.email == email)) == 0


async def test_email_of_soft_deleted_user_refused_once(client, factory):
    admin = await admin_headers(factory)
    email = f"gone_{uuid.uuid4().hex[:8]}@example.com"
    async with factory() as s:
        s.add(User(community_id=CID, email=email, username=f"g{uuid.uuid4().hex[:8]}",
                   display_name="Gone", deleted_at=datetime.now(UTC)))  # fmt: skip
        await s.commit()
    idp, slug = StubIdP(), f"ak{uuid.uuid4().hex[:6]}"
    with idp.serving():
        await _create(client, admin, idp, slug)
        cb = await sso_login(client, idp, slug, _claims(email))
    assert parse_qs(urlsplit(cb.headers["location"]).query)["error"] == ["sso_email_taken"]
    assert await count(factory, select(func.count()).where(User.email == email)) == 1
