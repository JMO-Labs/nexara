"""
@file test_password_service.py
@brief Unit tests for PasswordService (HIBP check and password reset flows).

Validates breach checking, reset token generation, and password update
using mocked dependencies.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import AuthenticationError
from app.services.password_service import PasswordService


def _make_settings(hibp_enabled: bool = True) -> MagicMock:
    """@brief Create mock app settings."""
    settings = MagicMock()
    settings.HIBP_CHECK_ENABLED = hibp_enabled
    return settings


class TestCheckHibp:
    """@brief Tests for PasswordService.check_hibp()."""

    @pytest.mark.asyncio
    async def test_returns_false_when_hibp_disabled(self):
        """check_hibp should return False when HIBP_CHECK_ENABLED is False."""
        settings = _make_settings(hibp_enabled=False)
        svc = PasswordService(session=AsyncMock(), settings=settings)

        result = await svc.check_hibp("any-password")

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_true_when_password_found_in_breach(self):
        """check_hibp should return True when the suffix matches a breach entry."""
        import hashlib

        password = "breached-password"
        sha1 = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()
        suffix = sha1[5:]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = f"{suffix}:42\nABCDE:10\n"

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)

        settings = _make_settings(hibp_enabled=True)
        svc = PasswordService(session=AsyncMock(), settings=settings)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await svc.check_hibp(password)

        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_api_fails(self):
        """check_hibp should return False on network/API errors (fail-open)."""
        settings = _make_settings(hibp_enabled=True)
        svc = PasswordService(session=AsyncMock(), settings=settings)

        with patch("httpx.AsyncClient", side_effect=Exception("network error")):
            result = await svc.check_hibp("some-password")

        assert result is False


class TestRequestPasswordReset:
    """@brief Tests for PasswordService.request_password_reset()."""

    @pytest.mark.asyncio
    async def test_returns_token_when_email_exists(self):
        """request_password_reset should return a raw token for known emails."""
        mock_user = MagicMock()
        mock_user.id = uuid.uuid4()

        session = AsyncMock()
        settings = _make_settings()

        svc = PasswordService(session=session, settings=settings)
        svc._user_repo = AsyncMock()
        svc._user_repo.find_by_email.return_value = mock_user
        svc._token_repo = AsyncMock()

        result = await svc.request_password_reset("user@example.com")

        assert result is not None
        assert isinstance(result, str)
        svc._token_repo.create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_returns_none_when_email_not_found(self):
        """request_password_reset should return None for unknown emails."""
        session = AsyncMock()
        settings = _make_settings()

        svc = PasswordService(session=session, settings=settings)
        svc._user_repo = AsyncMock()
        svc._user_repo.find_by_email.return_value = None

        result = await svc.request_password_reset("unknown@example.com")

        assert result is None


class TestResetPassword:
    """@brief Tests for PasswordService.reset_password()."""

    @pytest.mark.asyncio
    async def test_raises_on_invalid_token(self):
        """reset_password should raise AuthenticationError for invalid tokens."""
        session = AsyncMock()
        settings = _make_settings()

        svc = PasswordService(session=session, settings=settings)
        svc._token_repo = AsyncMock()
        svc._token_repo.find_by_hash.return_value = None

        with pytest.raises(AuthenticationError, match="Invalid or expired"):
            await svc.reset_password("bad-token", "new-password-12345")

    @pytest.mark.asyncio
    async def test_raises_on_expired_token(self):
        """reset_password should raise AuthenticationError for expired tokens."""
        stored = MagicMock()
        stored.revoked_at = None
        stored.expires_at = datetime.now(UTC) - timedelta(hours=2)

        session = AsyncMock()
        settings = _make_settings()

        svc = PasswordService(session=session, settings=settings)
        svc._token_repo = AsyncMock()
        svc._token_repo.find_by_hash.return_value = stored

        with pytest.raises(AuthenticationError, match="Invalid or expired"):
            await svc.reset_password("expired-token", "new-password-12345")
