"""
@file test_auth_magic_link.py
@brief Unit tests for magic link authentication flow.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import AuthenticationError
from app.models.auth import MagicLinkToken
from app.models.user import User
from app.services.auth_service import AuthService

USER_ID = uuid.uuid4()
USER_EMAIL = "alice@example.com"


def _make_user(user_id=USER_ID, email=USER_EMAIL):
    u = MagicMock(spec=User)
    u.id = user_id
    u.email = email
    u.is_active = True
    u.two_factor_enabled = False
    return u


@pytest.fixture(autouse=True)
def _sso_only_off():
    """@brief SSO-only guard disabled by default (mocked sessions)."""
    with patch("app.services.auth.sso_only.is_sso_only", AsyncMock(return_value=False)):
        yield


def _make_service(session=None, settings=None):
    session = session or AsyncMock()
    settings = settings or MagicMock()
    settings.COMMUNITY_ID = str(uuid.uuid4())
    settings.APP_BASE_URL = "https://app.example.com"
    settings.SMTP_FROM = "noreply@example.com"
    settings.SECRET_KEY = "test-secret"
    settings.JWT_ALGORITHM = "HS256"
    settings.ACCESS_TOKEN_EXPIRE_MINUTES = 15
    settings.REFRESH_TOKEN_EXPIRE_DAYS = 30
    return AuthService(session, settings)


class TestRequestMagicLink:
    @pytest.mark.asyncio
    async def test_request_magic_link_sends_email(self):
        user = _make_user()
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()

        with patch("app.services.auth_service.UserRepository") as mock_user_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.find_by_email = AsyncMock(return_value=user)
            mock_user_repo_cls.return_value = mock_repo

            with patch("app.services.auth.magic_link.send_email") as mock_send:
                mock_send.delay = MagicMock()
                service = _make_service(session=session)
                await service.request_magic_link(USER_EMAIL)
                mock_send.delay.assert_called_once()

    @pytest.mark.asyncio
    async def test_request_magic_link_unknown_email_returns_none(self):
        with patch("app.services.auth_service.UserRepository") as mock_user_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.find_by_email = AsyncMock(return_value=None)
            mock_user_repo_cls.return_value = mock_repo

            service = _make_service()
            result = await service.request_magic_link("unknown@example.com")
            assert result is None


class TestVerifyMagicLink:
    @pytest.mark.asyncio
    async def test_verify_valid_token_issues_session(self):
        user = _make_user()
        token = MagicMock(spec=MagicLinkToken)
        token.user_id = user.id
        token.expires_at = datetime.now(UTC) + timedelta(minutes=10)
        token.consumed_at = None

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = token
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.flush = AsyncMock()

        mock_repo = AsyncMock()
        mock_repo.get_by_id = AsyncMock(return_value=user)

        service = _make_service(session=mock_session)
        service._user_repo = mock_repo

        with patch(
            "app.services.auth_service._issue_tokens_impl", new_callable=AsyncMock
        ) as mock_issue:
            mock_issue.return_value = {
                "access_token": "jwt-token",
                "expires_in": 900,
                "raw_refresh_token": "refresh-token",
            }
            result = await service.verify_magic_link("raw-token-uuid")

            assert result["access_token"] == "jwt-token"
            assert token.consumed_at is not None

    @pytest.mark.asyncio
    async def test_verify_expired_token_raises(self):
        token = MagicMock(spec=MagicLinkToken)
        token.expires_at = datetime.now(UTC) - timedelta(minutes=1)
        token.consumed_at = None

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = token
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = _make_service(session=mock_session)

        with pytest.raises(AuthenticationError):
            await service.verify_magic_link("expired-token")

    @pytest.mark.asyncio
    async def test_verify_consumed_token_raises(self):
        token = MagicMock(spec=MagicLinkToken)
        token.expires_at = datetime.now(UTC) + timedelta(minutes=10)
        token.consumed_at = datetime.now(UTC) - timedelta(minutes=5)

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = token
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = _make_service(session=mock_session)

        with pytest.raises(AuthenticationError):
            await service.verify_magic_link("consumed-token")
