# ruff: noqa: E501
"""
@file test_google_oauth.py
@brief Google OAuth for mail: token refresh + cache, XOAUTH2, sender wiring, connect flow.
"""

from __future__ import annotations

import base64
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.core.config import Settings
from app.core.encryption import derive_fernet_key, encrypt_secret
from app.core.exceptions import AuthorizationError
from app.services.email import google_oauth as go
from app.services.email.sender import SmtpSendError, send_email
from app.services.email.smtp_settings import SmtpConfig, config_from_row


class FakeValkey:
    def __init__(self):
        self.d: dict[str, str] = {}
        self.ttl: dict[str, int] = {}

    async def get(self, k):
        return self.d.get(k)

    async def set(self, k, v, ex=None):
        self.d[k] = v
        self.ttl[k] = ex

    async def getdel(self, k):
        return self.d.pop(k, None)

    async def aclose(self):
        pass


def _cfg(**kw) -> SmtpConfig:
    base = {
        "host": "smtp.gmail.com",
        "port": 587,
        "security": "starttls",
        "user": "me@gmail.com",
        "password": "",
        "from_addr": "me@gmail.com",
        "auth": "google_oauth",
        "google_refresh": "r-tok",
        "google_client_id": "cid",
        "google_client_secret": "csec",
        "community_id": uuid.uuid4(),
    }
    return SmtpConfig(**{**base, **kw})


def _client(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


class TestXoauth2:
    def test_exact_string(self):
        raw = base64.b64decode(go.xoauth2_string("a@b.c", "tok"))
        assert raw == b"user=a@b.c\x01auth=Bearer tok\x01\x01"


class TestAccessToken:
    async def test_refresh_then_cached(self):
        calls = []

        def handler(req: httpx.Request) -> httpx.Response:
            calls.append(req)
            return httpx.Response(200, json={"access_token": "at1", "expires_in": 3600})

        vk = FakeValkey()
        with (
            patch.object(go, "_valkey", return_value=vk),
            patch.object(go, "_http", lambda: _client(handler)),
        ):
            assert await go.google_access_token(_cfg()) == "at1"
            assert await go.google_access_token(_cfg()) == "at1"
        assert len(calls) == 1
        body = calls[0].content.decode()
        assert "grant_type=refresh_token" in body and "refresh_token=r-tok" in body
        assert str(calls[0].url) == "https://oauth2.googleapis.com/token"
        assert list(vk.ttl.values()) == [3540]

    async def test_invalid_grant_is_auth_failed_without_raw_text(self):
        def handler(_):
            return httpx.Response(
                400, json={"error": "invalid_grant", "error_description": "r-tok"}
            )

        with (
            patch.object(go, "_valkey", return_value=FakeValkey()),
            patch.object(go, "_http", lambda: _client(handler)),
            pytest.raises(SmtpSendError) as ei,
        ):
            await go.google_access_token(_cfg())
        assert ei.value.category == "auth_failed" and "r-tok" not in ei.value.message

    async def test_not_connected(self):
        with pytest.raises(SmtpSendError) as ei:
            await go.google_access_token(_cfg(google_refresh=None))
        assert ei.value.category == "auth_failed"

    async def test_env_client_fallback(self):
        seen = {}

        def handler(req):
            seen["b"] = req.content.decode()
            return httpx.Response(200, json={"access_token": "t", "expires_in": 3600})

        s = Settings(GOOGLE_MAIL_CLIENT_ID="eid", GOOGLE_MAIL_CLIENT_SECRET="esec")
        with (
            patch.object(go, "_valkey", return_value=FakeValkey()),
            patch.object(go, "_http", lambda: _client(handler)),
            patch.object(go, "get_settings", return_value=s),
        ):
            await go.google_access_token(_cfg(google_client_id="", google_client_secret=""))
        assert "client_id=eid" in seen["b"] and "client_secret=esec" in seen["b"]


class TestSenderXoauth2:
    async def test_google_auth_uses_auth_xoauth2(self):
        ctx = MagicMock(send_message=AsyncMock(), auth_xoauth2=AsyncMock())
        ctx.__aenter__ = AsyncMock(return_value=ctx)
        ctx.__aexit__ = AsyncMock(return_value=None)
        with (
            patch("app.services.email.sender.SMTP", return_value=ctx) as smtp,
            patch("app.services.email.sender._record", new=AsyncMock()),
            patch("app.services.email.sender.google_access_token", AsyncMock(return_value="at")),
        ):
            await send_email(_cfg(), "u@e.com", "S", "<p>x</p>", "x")
        ctx.auth_xoauth2.assert_awaited_once_with("me@gmail.com", "at")
        kw = smtp.call_args.kwargs
        assert kw["username"] is None and kw["password"] is None and kw["start_tls"] is True

    async def test_password_auth_ignores_unreadable_refresh(self):
        row = SimpleNamespace(
            id="cid", smtp_host="h", smtp_port=587, smtp_security="starttls", smtp_user="u",
            smtp_password=encrypt_secret("pw", derive_fernet_key("k")), smtp_from=None,
            smtp_from_name=None, smtp_auth="password", smtp_google_refresh="garbage",
        )  # fmt: skip
        assert config_from_row(row, "k").secret_unreadable is False
        row.smtp_auth = "google_oauth"
        assert config_from_row(row, "k").secret_unreadable is True


def _row(**kw):
    base = dict(
        id=uuid.uuid4(), smtp_host=None, smtp_port=None, smtp_security=None, smtp_user=None,
        smtp_password=None, smtp_from=None, smtp_from_name=None, smtp_auth="password",
        smtp_google_refresh=None, smtp_google_client_id=None, smtp_google_client_secret=None,
        smtp_last_ok_at=None, smtp_last_error=None,
    )  # fmt: skip
    return SimpleNamespace(**{**base, **kw})


class TestConnectFlow:
    def _svc(self, role="admin", row=None):
        from app.services.admin_google_mail import GoogleMailService

        row = row or _row()
        repo = AsyncMock()
        repo.get.return_value = row

        async def upd(_c, v):
            for k, val in v.items():
                setattr(row, k, val)
            return row

        repo.update_smtp.side_effect = upd
        users = AsyncMock()
        users.get_by_id.return_value = SimpleNamespace(
            id=uuid.uuid4(), role=role, community_id=uuid.UUID(Settings().COMMUNITY_ID)
        )
        s = Settings(GOOGLE_MAIL_CLIENT_ID="cid", GOOGLE_MAIL_CLIENT_SECRET="csec")
        vk = FakeValkey()
        return GoogleMailService(repo, users, s, vk), row, vk, users

    async def test_start_stores_state_10min_and_builds_url(self):
        svc, _, vk, _ = self._svc()
        url = await svc.start(uuid.uuid4())
        assert url.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
        for frag in ("access_type=offline", "prompt=consent", "client_id=cid", "mail.google.com"):
            assert frag in url
        assert (
            "redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Fapi%2Fv1%2Fadmin%2Femail%2Fgoogle%2Fcallback"
            in url
        )
        assert list(vk.ttl.values()) == [600]

    async def test_start_without_client_is_error(self):
        from app.core.exceptions import AppError

        svc, row, _, _ = self._svc()
        svc._settings = Settings()
        with pytest.raises(AppError):
            await svc.start(uuid.uuid4())

    async def test_callback_sets_all_fields_in_one_update_and_keeps_refresh(self):
        svc, row, vk, _ = self._svc(row=_row(smtp_host="old.example.com", smtp_user="old"))
        await svc.start(uuid.uuid4())
        state = next(k for k in vk.d).split(":")[-1]
        with patch(
            "app.services.admin_google_mail.exchange_code",
            AsyncMock(return_value=("refresh-1", "me@gmail.com")),
        ):
            await svc.complete("code", state)
        assert (row.smtp_host, row.smtp_port, row.smtp_security) == (
            "smtp.gmail.com",
            587,
            "starttls",
        )
        assert row.smtp_user == "me@gmail.com" and row.smtp_auth == "google_oauth"
        assert row.smtp_from == "me@gmail.com"
        dec = config_from_row(row, Settings().SECRET_KEY)
        assert dec.google_refresh == "refresh-1" and dec.password == ""
        assert not vk.d  # state consumed

    async def test_state_single_use_and_unknown_rejected(self):
        svc, _, vk, _ = self._svc()
        await svc.start(uuid.uuid4())
        state = next(k for k in vk.d).split(":")[-1]
        with patch(
            "app.services.admin_google_mail.exchange_code", AsyncMock(return_value=("r", "e@g.com"))
        ):
            await svc.complete("c", state)
            with pytest.raises(AuthorizationError):
                await svc.complete("c", state)
            with pytest.raises(AuthorizationError):
                await svc.complete("c", "nope")

    async def test_non_admin_initiator_rejected(self):
        svc, row, vk, _ = self._svc(role="member")
        await svc.start(uuid.uuid4())
        state = next(k for k in vk.d).split(":")[-1]
        with patch("app.services.admin_google_mail.exchange_code", AsyncMock()) as ex:
            with pytest.raises(AuthorizationError):
                await svc.complete("c", state)
        ex.assert_not_called()
        assert row.smtp_google_refresh is None


class TestExchange:
    async def test_exchange_returns_refresh_and_email_from_id_token(self):
        import json

        def b64(d):
            return base64.urlsafe_b64encode(json.dumps(d).encode()).decode().rstrip("=")

        idt = f"{b64({'alg': 'none'})}.{b64({'email': 'me@gmail.com'})}.sig"

        def handler(req):
            assert "grant_type=authorization_code" in req.content.decode()
            return httpx.Response(
                200, json={"refresh_token": "rt", "id_token": idt, "access_token": "a"}
            )

        with patch.object(go, "_http", lambda: _client(handler)):
            assert await go.exchange_code("cid", "sec", "http://x/cb", "code") == (
                "rt",
                "me@gmail.com",
            )

    async def test_exchange_without_refresh_token_fails(self):
        def handler(_):
            return httpx.Response(200, json={"access_token": "a"})

        from app.core.exceptions import AppError

        with patch.object(go, "_http", lambda: _client(handler)), pytest.raises(AppError):
            await go.exchange_code("cid", "sec", "http://x/cb", "code")


class TestCallbackRoute:
    async def _get(self, test_app, query, side_effect=None):
        from httpx import ASGITransport, AsyncClient

        from app.core.dependencies import get_google_mail_service

        svc = AsyncMock()
        svc.complete.side_effect = side_effect
        test_app.dependency_overrides[get_google_mail_service] = lambda: svc
        try:
            async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://t") as c:
                return await c.get("/api/v1/admin/email/google/callback" + query), svc
        finally:
            test_app.dependency_overrides.clear()

    async def test_success_redirects_to_email_tab_without_auth(self, test_app):
        r, svc = await self._get(test_app, "?code=c&state=s")
        assert (
            r.status_code == 303
            and r.headers["location"] == "/app/admin?tab=email&google=connected"
        )
        svc.complete.assert_awaited_once_with("c", "s")

    async def test_bad_state_and_denied_redirect_with_error(self, test_app):
        r, _ = await self._get(test_app, "?code=c&state=s", AuthorizationError())
        assert r.headers["location"].endswith("google=error")
        r, svc = await self._get(test_app, "?error=access_denied&state=s")
        assert r.headers["location"].endswith("google=error")
        svc.complete.assert_not_awaited()
