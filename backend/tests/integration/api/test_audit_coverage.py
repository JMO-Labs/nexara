# ruff: noqa: F811
"""
@file test_audit_coverage.py
@brief Each security-relevant route writes exactly one audit row (real Postgres, real services).
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qs, urlsplit

import pyotp
from cryptography.fernet import Fernet

import app.models  # noqa: F401
from app.services.oauth.email_change import notify_email_synced
from app.services.oauth.profile_sync import audit_role_synced
from tests.helpers.webauthn_soft import Auth
from tests.integration.api.audit_world import CID, PW, FakeValkey, one, world  # noqa: F401


async def test_email_settings_and_google_connect(world):
    w = world
    body = {
        "host": "smtp.gmail.com",
        "port": 587,
        "security": "starttls",
        "user": "me@gmail.com",
        "password": "abcd efgh ijkl mnop",
        "from_addr": "me@gmail.com",
    }
    async with w.client() as c:
        assert (await c.put("/api/v1/admin/email", json=body)).status_code == 200
        r = await one(w, "email.settings.updated", actor=w.admin.id, target_id=CID)
        assert "abcd" not in str(r.extra_data)

        start = await c.get("/api/v1/admin/email/google/start")
        assert start.status_code == 200, start.text
        state = parse_qs(urlsplit(start.json()["url"]).query)["state"][0]
        nonce = start.headers["set-cookie"].split("nx_gmail_nonce=")[1].split(";")[0]
        with patch(
            "app.services.admin_google_mail.exchange_code",
            AsyncMock(return_value=("refresh-token-xyz", "me@gmail.com")),
        ):
            cb = await c.get(
                f"/api/v1/admin/email/google/callback?code=abc&state={state}",
                follow_redirects=False,
                headers={"cookie": f"nx_gmail_nonce={nonce}"},
            )
    assert cb.status_code == 303 and cb.headers["location"].endswith("google=connected")
    r = await one(w, "email.google.connected", actor=w.admin.id, target_id=CID)
    assert "refresh-token" not in str(r.extra_data)


async def test_apprise_targets_and_settings(world, monkeypatch):
    w = world
    monkeypatch.setenv("APPRISE_ENCRYPTION_KEY", Fernet.generate_key().decode())
    async with w.client() as c:
        r = await c.post(
            "/api/v1/admin/apprise/targets",
            json={"apprise_url": "json://example.com/hook", "label": "ops"},
        )
        assert r.status_code == 201, r.text
        tid = uuid.UUID(r.json()["id"])
        row = await one(w, "apprise.target.created", actor=w.admin.id, target_id=tid)
        assert "example.com" not in str(row.extra_data)
        with patch(
            "app.repositories.apprise_repo.AppriseRepository.test_send",
            AsyncMock(return_value=(True, "ok")),
        ):
            assert (await c.post(f"/api/v1/admin/apprise/targets/{tid}/test")).status_code == 200
        await one(w, "apprise.target.tested", actor=w.admin.id, target_id=tid)
        r = await c.put("/api/v1/admin/apprise/settings", json={"allow_local": True})
        assert r.status_code == 200
        got = await w.rows("apprise.settings.updated")
        assert len(got) == 1 and got[0].actor_id == w.admin.id
        assert (await c.delete(f"/api/v1/admin/apprise/targets/{tid}")).status_code == 200
        await one(w, "apprise.target.deleted", actor=w.admin.id, target_id=tid)


async def test_two_factor_lifecycle(world):
    w = world
    async with w.client(w.member) as c:
        r = await c.post("/api/v1/auth/2fa/totp/start")
        assert r.status_code == 200, r.text
        secret = r.json()["secret"]
        r = await c.post("/api/v1/auth/2fa/totp/confirm", json={"code": pyotp.TOTP(secret).now()})
        assert r.status_code == 200, r.text
        codes = r.json()["recovery_codes"]
        await one(w, "2fa.enabled", actor=w.member.id, target_id=w.member.id, target_type="user")
        r = await c.post("/api/v1/auth/2fa/recovery/regenerate", json={"code": codes[0]})
        assert r.status_code == 200, r.text
        await one(w, "2fa.recovery_regenerated", actor=w.member.id, target_id=w.member.id)
        r = await c.post("/api/v1/auth/2fa/totp/disable", json={"password": PW})
        assert r.status_code == 200, r.text
        await one(w, "2fa.disabled", actor=w.member.id, target_id=w.member.id)


async def test_admin_2fa_reset_and_policy(world):
    w = world
    async with w.client() as c:
        r = await c.post(f"/api/v1/admin/users/{w.member.id}/reset-2fa")
        assert r.status_code == 200, r.text
        await one(w, "admin.user.2fa_reset", actor=w.admin.id, target_id=w.member.id)
        r = await c.put("/api/v1/admin/security", json={"require_2fa": "admins"})
        assert r.status_code == 200, r.text
        await one(w, "admin.security.updated", actor=w.admin.id, target_id=CID)


async def test_passkey_add_remove(world):
    w = world
    auth = Auth()
    with patch("app.services.auth.passkeys.get_pool", return_value=FakeValkey()):
        await _passkey_flow(w, auth)


async def _passkey_flow(w, auth):
    async with w.client(w.member) as c:
        ro = await c.post("/api/v1/auth/passkeys/register/options")
        assert ro.status_code == 200, ro.text
        opts = ro.json()
        r = await c.post(
            "/api/v1/auth/passkeys/register/verify",
            json={"credential": auth.create(opts), "name": "K"},
        )
        assert r.status_code == 200, r.text
        pid = uuid.UUID(r.json()["id"])
        await one(w, "passkey.added", actor=w.member.id, target_id=pid, target_type="passkey")
        assert (await c.delete(f"/api/v1/auth/passkeys/{pid}")).status_code == 200
        await one(w, "passkey.removed", actor=w.member.id, target_id=pid)


async def test_sso_provider_crud(world):
    w = world
    body = {
        "slug": f"idp{uuid.uuid4().hex[:6]}",
        "display_name": "IdP",
        "provider_type": "oauth2",
        "client_id": "id",
        "client_secret": "SUPERSECRET",
        "authorization_endpoint": "https://idp.example/a",
        "token_endpoint": "https://idp.example/t",
        "userinfo_endpoint": "https://idp.example/u",
    }
    async with w.client() as c:
        r = await c.post("/api/v1/admin/oauth/providers", json=body)
        assert r.status_code == 201, r.text
        pid = uuid.UUID(r.json()["id"])
        row = await one(w, "oauth.provider.created", actor=w.admin.id, target_id=pid)
        r = await c.put(
            f"/api/v1/admin/oauth/providers/{pid}",
            json={"display_name": "Renamed", "client_secret": "NEWSECRET"},
        )
        assert r.status_code == 200, r.text
        upd = await one(w, "oauth.provider.updated", actor=w.admin.id, target_id=pid)
        assert (await c.post(f"/api/v1/admin/oauth/providers/{pid}/toggle")).status_code == 200
        await one(w, "oauth.provider.toggled", actor=w.admin.id, target_id=pid)
        assert (await c.delete(f"/api/v1/admin/oauth/providers/{pid}")).status_code == 200
        await one(w, "oauth.provider.deleted", actor=w.admin.id, target_id=pid)
    for r_ in (row, upd):
        assert "SECRET" not in str(r_.extra_data)


async def test_sso_sync_events_are_system_actions(world):
    w = world
    await audit_role_synced(w.s, w.member.id, "member", "admin")
    r = await one(w, "sso.role_synced", actor=None, target_id=w.member.id, target_type="user")
    assert r.extra_data["new_role"] == "admin"
    with patch("app.services.oauth.email_change.send_email", create=True):
        try:
            await notify_email_synced(
                w.s,
                user_id=w.member.id,
                community_id=CID,
                provider_id=None,
                old_email="a@x.dev",
                new_email="b@x.dev",
            )
        except Exception:  # mail/token side effects are out of scope here
            pass
    await one(w, "sso.email_synced", actor=None, target_id=w.member.id, target_type="user")


async def test_data_export_started(world):
    w = world
    enq = SimpleNamespace(calls=[])
    from app.api.v1 import export

    w.app.dependency_overrides[export._get_enqueue] = lambda: lambda u, e: enq.calls.append(e)
    w.app.dependency_overrides[export._get_redis] = lambda: FakeValkey()
    async with w.client(w.member) as c:
        r = await c.post("/api/v1/export/request")
    assert r.status_code == 200, r.text
    await one(
        w,
        "data_export.started",
        actor=w.member.id,
        target_id=uuid.UUID(r.json()["export_id"]),
        target_type="user_export",
    )
