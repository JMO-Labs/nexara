"""
@file test_sso_callback_failures.py
@brief Every SSO callback failure is a browser redirect, rolls back, and is logged.

Real Postgres + Valkey, stubbed OIDC IdP. Non-refusal failures -> 302
/login?error=sso_failed with no user row and a failed signin_events row;
refusals -> /login?error=<code> with a signin_events row; admin test-login
failures -> /sso-test?error=sso_failed.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qs, urlsplit

import pytest
from sqlalchemy import func, select

from app.core.exceptions import AppError
from app.models.user import User
from tests.integration.api.sso_idp import (
    StubIdP,
    admin_headers,
    client_fixture,  # noqa: F401
    count,
    factory_fixture,  # noqa: F401
    failed,
    provider_body,
    sso_failures,
    sso_login,
    start_login,
)


def _claims(email: str, **extra) -> dict:
    return {"sub": f"ak-{uuid.uuid4().hex}", "email": email, "email_verified": True, **extra}


async def _provider(client, factory, idp, **over) -> str:
    admin = await admin_headers(factory)
    slug = f"ak{uuid.uuid4().hex[:6]}"
    r = await client.post(
        "/api/v1/admin/oauth/providers", json=provider_body(idp, slug, **over), headers=admin
    )
    assert r.status_code == 201, r.text
    return slug


async def _no_user(factory, email: str) -> bool:
    return await count(factory, select(func.count()).where(User.email == email)) == 0


@pytest.mark.parametrize("mode", ["token_400", "userinfo_500", "bad_id_token"])
async def test_idp_failures_redirect_and_log(client, factory, mode):
    idp = StubIdP()
    email = f"f_{uuid.uuid4().hex[:8]}@example.com"
    reason = (
        "callback:HTTPStatusError" if mode == "userinfo_500" else "callback:AuthenticationError"
    )
    before = await count(factory, sso_failures(reason))
    with idp.serving():
        slug = await _provider(client, factory, idp)
        if mode == "token_400":
            idp.token_status = 400
        elif mode == "userinfo_500":
            idp.id_token, idp.userinfo_status = False, 500
        if mode != "bad_id_token":
            cb = await sso_login(client, idp, slug, _claims(email))
        else:  # ID token signed for another nonce -> verification fails
            state, cookies, _ = await start_login(client, slug)
            cookies.pop("_nonce")
            idp.nonce, idp.claims = "other", _claims(email)
            cb = await client.get(
                f"/api/v1/oauth/{slug}/callback",
                params={"code": "c", "state": state},
                cookies=cookies,
                follow_redirects=False,
            )
    assert failed(cb), cb.text
    assert await _no_user(factory, email)
    assert await count(factory, sso_failures(reason)) == before + 1


async def test_idp_error_param_redirects(client, factory):
    """?error=access_denied (no code) must not be a FastAPI 422."""
    idp = StubIdP()
    with idp.serving():
        slug = await _provider(client, factory, idp)
        state, cookies, _ = await start_login(client, slug)
        cookies.pop("_nonce")
        cb = await client.get(
            f"/api/v1/oauth/{slug}/callback",
            params={"error": "access_denied", "state": state},
            cookies=cookies,
            follow_redirects=False,
        )
    assert failed(cb)
    assert await count(factory, sso_failures("idp_error:access_denied")) >= 1


async def test_bad_state_redirects(client, factory):
    idp = StubIdP()
    before = await count(factory, sso_failures("invalid_state"))
    with idp.serving():
        slug = await _provider(client, factory, idp)
        _state, cookies, _ = await start_login(client, slug)
        cookies.pop("_nonce")
        cb = await client.get(
            f"/api/v1/oauth/{slug}/callback",
            params={"code": "c", "state": "forged"},
            cookies=cookies,
            follow_redirects=False,
        )
    assert failed(cb)
    assert await count(factory, sso_failures("invalid_state")) == before + 1


async def test_provision_conflict_rolls_back_half_created_user(client, factory):
    """A failure after the user insert must not commit the half-provisioned user."""
    idp = StubIdP()
    email = f"half_{uuid.uuid4().hex[:8]}@example.com"
    boom = AppError(code="sso_provision_conflict", message="x", status_code=409)
    with idp.serving():
        slug = await _provider(client, factory, idp)
        with patch(
            "app.services.oauth.user_provisioner.CalendarRepository.ensure_personal",
            AsyncMock(side_effect=boom),
        ):
            cb = await sso_login(client, idp, slug, _claims(email))
    assert failed(cb)
    assert await _no_user(factory, email)
    assert await count(factory, sso_failures("callback:AppError")) >= 1


async def test_refusal_is_logged(client, factory):
    idp = StubIdP()
    email = f"r_{uuid.uuid4().hex[:8]}@example.com"
    before = await count(factory, sso_failures("sso_group_required"))
    with idp.serving():
        slug = await _provider(client, factory, idp, required_group="nexara-users")
        cb = await sso_login(client, idp, slug, _claims(email, groups=["others"]))
    query = parse_qs(urlsplit(cb.headers["location"]).query)
    assert query["error"] == ["sso_group_required"]
    assert await count(factory, sso_failures("sso_group_required")) == before + 1
    assert await _no_user(factory, email)


async def test_test_login_failure_redirects_popup(client, factory):
    idp = StubIdP()
    admin = await admin_headers(factory)
    with idp.serving():
        slug = await _provider(client, factory, idp)
        listed = await client.get("/api/v1/admin/oauth/providers", headers=admin)
        pid = next(p["id"] for p in listed.json() if p["slug"] == slug)
        r = await client.post(f"/api/v1/admin/oauth/providers/{pid}/test-login", headers=admin)
        state = parse_qs(urlsplit(r.json()["authorize_url"]).query)["state"][0]
        bind = r.headers["set-cookie"].split(";", 1)[0].split("=", 1)
        idp.token_status = 400
        cb = await client.get(
            f"/api/v1/oauth/{slug}/callback",
            params={"code": "c", "state": state},
            cookies={bind[0]: bind[1]},
            follow_redirects=False,
        )
    assert cb.status_code == 302
    assert cb.headers["location"].endswith("/sso-test?error=sso_failed")


async def test_unknown_provider_login_redirects(client, factory):
    r = await client.get(f"/api/v1/oauth/nope{uuid.uuid4().hex[:6]}/login", follow_redirects=False)
    assert failed(r)
