"""
@file test_auth_security_fixes.py
@brief Tests for 2FA bypass fixes (enroll, magic link, TOTP replay, rate limit).
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pyotp
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.exceptions import AuthenticationError, AuthorizationError
from tests.unit.services.test_auth_service import (  # noqa: F401
    _make_service,
    _make_user,
    _sso_only_off,
)


class TestEnrollWhileEnabled:
    @pytest.mark.asyncio
    async def test_enroll_refused_when_enabled(self):
        svc = _make_service()
        user = _make_user(totp_enabled=True, totp_secret="SECRET")
        with pytest.raises(AuthorizationError, match="2fa_already_enabled"):
            await svc.enroll_2fa(user)
        svc._user_repo.update_totp.assert_not_called()

    @pytest.mark.asyncio
    async def test_enroll_ok_when_disabled(self):
        svc = _make_service()
        result = await svc.enroll_2fa(_make_user(totp_enabled=False))
        assert result["secret"]
        svc._user_repo.update_totp.assert_awaited_once()


class TestMagicLink2FA:
    @pytest.mark.asyncio
    async def test_magic_link_requires_2fa(self):
        svc = _make_service()
        user = _make_user(totp_enabled=True, totp_secret="SECRET")
        with patch(
            "app.services.auth_service._verify_magic_link_impl", AsyncMock(return_value=user)
        ):
            result = await svc.verify_magic_link("tok")
        assert result["requires_2fa"] is True
        assert result["two_factor_token"]
        assert "access_token" not in result

    @pytest.mark.asyncio
    async def test_magic_link_without_2fa_issues_tokens(self):
        svc = _make_service()
        user = _make_user(totp_enabled=False)
        tokens = {"access_token": "a", "expires_in": 1, "raw_refresh_token": "r"}
        with (
            patch(
                "app.services.auth_service._verify_magic_link_impl", AsyncMock(return_value=user)
            ),
            patch("app.services.auth_service._issue_tokens_impl", AsyncMock(return_value=tokens)),
        ):
            assert await svc.verify_magic_link("tok") == tokens


class TestTotpReplay:
    @pytest.mark.asyncio
    async def test_same_code_twice_rejected(self):
        secret = pyotp.random_base32()
        code = pyotp.TOTP(secret).now()
        svc = _make_service()
        user = _make_user(totp_enabled=True, totp_secret=secret)
        svc._user_repo.get_by_id.return_value = user
        svc._issue_tokens = AsyncMock(return_value={"access_token": "a"})
        redis = MagicMock()
        redis.set = AsyncMock(side_effect=[True, None])  # NX: second set fails
        from app.core.security import create_2fa_pending_token

        tok = create_2fa_pending_token(user.id, settings=svc._settings)
        with patch("app.services.auth.totp_replay.get_pool", return_value=redis):
            await svc.verify_2fa_login(two_factor_token=tok, code=code)
            with pytest.raises(AuthenticationError):
                await svc.verify_2fa_login(two_factor_token=tok, code=code)
        key = f"totp:used:{user.id}:{code}"
        redis.set.assert_awaited_with(key, "1", nx=True, ex=90)


class TestPushUnsubscribeScoped:
    @pytest.mark.asyncio
    async def test_other_user_deletes_nothing(self):
        from app.repositories.push_repo import PushSubscriptionRepository
        from app.services.push_service import PushService

        repo = AsyncMock(spec=PushSubscriptionRepository)
        svc = PushService(
            push_repo=repo,
            settings_repo=AsyncMock(),
            community_id=uuid.uuid4(),
            settings=MagicMock(),
        )
        uid = uuid.uuid4()
        await svc.unsubscribe(uid, "https://e/1")
        repo.delete_by_endpoint.assert_awaited_once_with("https://e/1", user_id=uid)


class Test2FALoginRateLimit:
    @pytest.mark.asyncio
    async def test_11th_request_429(self, test_app):
        with patch(
            "app.api.v1.auth.AuthService.verify_2fa_login",
            AsyncMock(side_effect=AuthenticationError(message="bad")),
        ):
            transport = ASGITransport(app=test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                codes = []
                for _ in range(11):
                    r = await c.post(
                        "/api/v1/auth/2fa/login",
                        json={"two_factor_token": "x", "code": "123456"},
                    )
                    codes.append(r.status_code)
        assert codes[:10] == [401] * 10
        assert codes[10] == 429
