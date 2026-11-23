"""
@file test_signin_recording.py
@brief Every sign-in path records exactly one success row, and none at a 2FA first step.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pyotp
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import create_2fa_pending_token
from tests.unit.services.test_auth_security_fixes import _fake_redis
from tests.unit.services.test_auth_service import (  # noqa: F401
    _make_service,
    _make_user,
    _sso_only_off,
)

LOG = "app.services.auth_service.log_success"


class TestPasswordLogin:
    @pytest.mark.asyncio
    async def test_success_records_once(self):
        svc = _make_service()
        svc._user_repo.find_by_email.return_value = _make_user()
        svc._issue_tokens = AsyncMock(return_value={"access_token": "a"})
        with patch(LOG, AsyncMock()) as log:
            await svc.login(email="test@example.com", password="valid-password1")
        log.assert_awaited_once()
        assert log.await_args.args[3] == "password"

    @pytest.mark.asyncio
    async def test_totp_user_first_step_records_nothing(self):
        svc = _make_service()
        svc._user_repo.find_by_email.return_value = _make_user(totp_enabled=True, totp_secret="S")
        with patch(LOG, AsyncMock()) as log:
            res = await svc.login(email="test@example.com", password="valid-password1")
        assert res["requires_2fa"] is True
        log.assert_not_awaited()


class TestVerify2faLogin:
    async def _go(self, backup: bool):
        secret = pyotp.random_base32()
        svc = _make_service()
        user = _make_user(totp_enabled=True, totp_secret=secret)
        svc._user_repo.get_by_id.return_value = user
        svc._issue_tokens = AsyncMock(return_value={"access_token": "a"})
        svc._try_backup_code = AsyncMock(return_value=backup)
        code = pyotp.TOTP(secret).now() if not backup else "ABCD1234"
        tok = create_2fa_pending_token(user.id, settings=svc._settings)
        with (
            patch("app.services.auth.totp_replay.get_pool", return_value=_fake_redis()),
            patch(LOG, AsyncMock()) as log,
        ):
            await svc.verify_2fa_login(two_factor_token=tok, code=code)
        return log

    @pytest.mark.asyncio
    async def test_totp_records_once(self):
        log = await self._go(backup=False)
        log.assert_awaited_once()
        assert log.await_args.args[3] == "totp"

    @pytest.mark.asyncio
    async def test_recovery_records_once(self):
        log = await self._go(backup=True)
        log.assert_awaited_once()
        assert log.await_args.args[3] == "recovery"


class TestMagicLink:
    @pytest.mark.asyncio
    async def test_totp_user_records_nothing_at_link_step(self):
        svc = _make_service()
        user = _make_user(totp_enabled=True, totp_secret="S")
        with (
            patch(
                "app.services.auth_service._verify_magic_link_impl", AsyncMock(return_value=user)
            ),
            patch(LOG, AsyncMock()) as log,
        ):
            res = await svc.verify_magic_link("tok")
        assert res["requires_2fa"] is True
        log.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_route_returns_requires_2fa(self, test_app):
        with patch(
            "app.api.v1.auth_magic_link.AuthService.verify_magic_link",
            AsyncMock(return_value={"requires_2fa": True, "two_factor_token": "pend"}),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=test_app), base_url="http://test"
            ) as c:
                r = await c.get("/api/v1/auth/magic-link/verify", params={"token": "x"})
        assert r.status_code == 200
        body = r.json()
        assert body["requires_2fa"] is True
        assert body["two_factor_token"] == "pend"
        assert not body.get("access_token")
        assert "refresh_token" not in r.cookies


class TestLockedOutAttempt:
    @pytest.mark.asyncio
    async def test_locked_out_failure_logged_with_user(self):
        from app.core.exceptions import AuthenticationError

        svc = _make_service()
        user = _make_user(totp_enabled=True, totp_secret="S")
        svc._user_repo.get_by_id.return_value = user
        tok = create_2fa_pending_token(user.id, settings=svc._settings)
        with (
            patch("app.services.auth_service.reserve_attempt", AsyncMock(return_value=False)),
            patch("app.services.auth_service.log_failure", AsyncMock()) as fail,
        ):
            with pytest.raises(AuthenticationError):
                await svc.verify_2fa_login(two_factor_token=tok, code="000000")
        assert fail.await_args.args[1] is user
