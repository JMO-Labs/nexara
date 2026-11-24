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

from app.core.exceptions import AuthenticationError
from tests.unit.services.test_auth_service import (  # noqa: F401
    _make_service,
    _make_user,
    _sso_only_off,
)


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
        redis = _fake_redis()
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


class _FakePipe:
    def __init__(self, r):
        self.r, self.ops = r, []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    def incr(self, k):
        self.ops.append(("incr", k))

    def expire(self, k, ttl, nx=False):
        self.ops.append(("expire", k, ttl, nx))

    async def execute(self):
        out = []
        for op in self.ops:
            if op[0] == "incr":
                self.r.store[op[1]] = self.r.store.get(op[1], 0) + 1
                out.append(self.r.store[op[1]])
            else:
                if not (op[3] and op[1] in self.r.ttl):
                    self.r.ttl[op[1]] = op[2]
                out.append(True)
        return out


class _FakeRedis:
    """@brief In-memory Valkey stand-in with TTL bookkeeping."""

    def __init__(self):
        self.store: dict = {}
        self.ttl: dict = {}

    def pipeline(self, transaction=True):
        return _FakePipe(self)

    async def set(self, k, v, nx=False, ex=None):
        if nx and k in self.store:
            return None
        self.store[k] = 1
        return True

    async def delete(self, k):
        self.store.pop(k, None)


def _fake_redis():
    return _FakeRedis()


class TestAttemptCapAndNormalise:
    async def _setup(self):
        secret = pyotp.random_base32()
        svc = _make_service()
        user = _make_user(totp_enabled=True, totp_secret=secret)
        svc._user_repo.get_by_id.return_value = user
        svc._try_backup_code = AsyncMock(return_value=False)
        svc._issue_tokens = AsyncMock(return_value={"access_token": "a"})
        from app.core.security import create_2fa_pending_token

        tok = create_2fa_pending_token(user.id, settings=svc._settings)
        return svc, secret, tok

    @pytest.mark.asyncio
    async def test_five_wrong_then_correct_rejected(self):
        svc, secret, tok = await self._setup()
        with patch("app.services.auth.totp_replay.get_pool", return_value=_fake_redis()):
            for _ in range(5):
                with pytest.raises(AuthenticationError):
                    await svc.verify_2fa_login(two_factor_token=tok, code="000000")
            with pytest.raises(AuthenticationError):
                await svc.verify_2fa_login(two_factor_token=tok, code=pyotp.TOTP(secret).now())

    @pytest.mark.asyncio
    async def test_fullwidth_digits_rejected(self):
        svc, secret, tok = await self._setup()
        full = "".join(chr(ord(c) + 0xFEE0) for c in pyotp.TOTP(secret).now())
        with patch("app.services.auth.totp_replay.get_pool", return_value=_fake_redis()):
            with pytest.raises(AuthenticationError):
                await svc.verify_2fa_login(two_factor_token=tok, code=full)

    @pytest.mark.asyncio
    async def test_whitespace_code_canonicalised(self):
        svc, secret, tok = await self._setup()
        code = pyotp.TOTP(secret).now()
        with patch("app.services.auth.totp_replay.get_pool", return_value=_fake_redis()):
            assert await svc.verify_2fa_login(two_factor_token=tok, code=f" {code} ")

    @pytest.mark.asyncio
    async def test_valkey_error_is_503(self):
        from redis.exceptions import ConnectionError as RedisConnErr

        from app.core.exceptions import AppError

        svc, secret, tok = await self._setup()
        r = _fake_redis()
        r.pipeline = MagicMock(side_effect=RedisConnErr("down"))
        with patch("app.services.auth.totp_replay.get_pool", return_value=r):
            with pytest.raises(AppError) as ei:
                await svc.verify_2fa_login(two_factor_token=tok, code="123456")
        assert ei.value.status_code == 503


class TestAccountCap:
    @pytest.mark.asyncio
    async def test_cap_across_tokens_and_reset(self):
        from app.core.security import create_2fa_pending_token

        svc = _make_service()
        secret = pyotp.random_base32()
        user = _make_user(totp_enabled=True, totp_secret=secret)
        svc._user_repo.get_by_id.return_value = user
        svc._try_backup_code = AsyncMock(return_value=False)
        svc._issue_tokens = AsyncMock(return_value={"access_token": "a"})
        redis = _fake_redis()
        with patch("app.services.auth.totp_replay.get_pool", return_value=redis):
            n = 0
            for _ in range(3):
                tok = create_2fa_pending_token(user.id, settings=svc._settings)
                for _ in range(4):
                    if n == 10:
                        break
                    with pytest.raises(AuthenticationError):
                        await svc.verify_2fa_login(two_factor_token=tok, code="000000")
                    n += 1
            tok = create_2fa_pending_token(user.id, settings=svc._settings)
            with pytest.raises(AuthenticationError):
                await svc.verify_2fa_login(two_factor_token=tok, code=pyotp.TOTP(secret).now())
            assert all(t > 0 for t in redis.ttl.values()) and redis.ttl

    @pytest.mark.asyncio
    async def test_success_resets_user_counter(self):
        from app.core.security import create_2fa_pending_token

        svc = _make_service()
        secret = pyotp.random_base32()
        user = _make_user(totp_enabled=True, totp_secret=secret)
        svc._user_repo.get_by_id.return_value = user
        svc._try_backup_code = AsyncMock(return_value=False)
        svc._issue_tokens = AsyncMock(return_value={"access_token": "a"})
        redis = _fake_redis()
        with patch("app.services.auth.totp_replay.get_pool", return_value=redis):
            tok = create_2fa_pending_token(user.id, settings=svc._settings)
            with pytest.raises(AuthenticationError):
                await svc.verify_2fa_login(two_factor_token=tok, code="000000")
            await svc.verify_2fa_login(two_factor_token=tok, code=pyotp.TOTP(secret).now())
        assert f"totp:fail:user:{user.id}" not in redis.store
