"""
@file test_dependencies.py
@brief Unit tests for FastAPI dependency factories: get_db, get_current_user, require_role.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.config import Settings
from app.core.dependencies import get_current_user, get_optional_user, require_role


def _make_settings() -> Settings:
    """@brief Settings for dependency tests (HS256)."""
    return Settings(
        SECRET_KEY="test-secret-deps",
        JWT_ALGORITHM="HS256",
    )


class TestGetCurrentUser:
    """@brief Token validation and user lookup tests."""

    @pytest.mark.asyncio
    async def test_missing_token_raises(self):
        from app.core.exceptions import AuthenticationError

        request = MagicMock()
        db = AsyncMock()
        settings = _make_settings()

        with pytest.raises(AuthenticationError, match="required"):
            await get_current_user(request=request, token=None, db=db, settings=settings)

    @pytest.mark.asyncio
    async def test_invalid_token_raises(self):
        from app.core.exceptions import AuthenticationError

        request = MagicMock()
        db = AsyncMock()
        settings = _make_settings()

        with pytest.raises(AuthenticationError):
            await get_current_user(
                request=request,
                token="invalid.jwt.token",
                db=db,
                settings=settings,
            )

    @pytest.mark.asyncio
    async def test_valid_token_returns_user(self):
        from app.core.security import create_access_token

        settings = _make_settings()
        user_id = uuid.uuid4()
        token = create_access_token(user_id, settings=settings)

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.is_active = True
        mock_user.deleted_at = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user

        db = AsyncMock()
        db.execute.return_value = mock_result
        request = MagicMock()

        user = await get_current_user(
            request=request,
            token=token,
            db=db,
            settings=settings,
        )
        assert user.id == user_id

    @pytest.mark.asyncio
    async def test_user_not_found_raises(self):
        from app.core.exceptions import AuthenticationError
        from app.core.security import create_access_token

        settings = _make_settings()
        token = create_access_token(uuid.uuid4(), settings=settings)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        db = AsyncMock()
        db.execute.return_value = mock_result
        request = MagicMock()

        with pytest.raises(AuthenticationError, match="not found"):
            await get_current_user(
                request=request,
                token=token,
                db=db,
                settings=settings,
            )


class TestRequireRole:
    """@brief Role-based authorization dependency tests."""

    @pytest.mark.asyncio
    async def test_allows_matching_role(self):
        mock_user = MagicMock()
        mock_user.role = "admin"

        checker = require_role("admin")
        result = await checker(current_user=mock_user)
        assert result.role == "admin"

    @pytest.mark.asyncio
    async def test_allows_any_of_multiple_roles(self):
        mock_user = MagicMock()
        mock_user.role = "member"

        checker = require_role("admin", "member")
        result = await checker(current_user=mock_user)
        assert result.role == "member"

    @pytest.mark.asyncio
    async def test_rejects_unauthorized_role(self):
        from app.core.exceptions import AuthorizationError

        mock_user = MagicMock()
        mock_user.role = "viewer"

        checker = require_role("admin")
        with pytest.raises(AuthorizationError, match="roles"):
            await checker(current_user=mock_user)


class TestGetOptionalUser:
    """@brief Optional user dependency tests."""

    @pytest.mark.asyncio
    async def test_returns_none_without_token(self):
        db = AsyncMock()
        settings = _make_settings()
        result = await get_optional_user(token=None, db=db, settings=settings)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_invalid_token(self):
        db = AsyncMock()
        settings = _make_settings()
        result = await get_optional_user(token="bad-token", db=db, settings=settings)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_user_with_valid_token(self):
        from app.core.security import create_access_token

        settings = _make_settings()
        user_id = uuid.uuid4()
        token = create_access_token(user_id, settings=settings)

        mock_user = MagicMock()
        mock_user.id = user_id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user

        db = AsyncMock()
        db.execute.return_value = mock_result

        result = await get_optional_user(token=token, db=db, settings=settings)
        assert result is not None
        assert result.id == user_id


class TestGetSuggestionService:
    """@brief Wiring of get_suggestion_service."""

    @pytest.mark.asyncio
    async def test_wires_repo_and_provider(self):
        from app.core.dependencies import get_suggestion_service
        from app.repositories.suggestion_repo import SuggestionRepository

        svc = await get_suggestion_service(
            db=AsyncMock(), settings=Settings(SECRET_KEY="x", AI_PROVIDER="")
        )
        assert isinstance(svc._repo, SuggestionRepository)
        assert svc._provider is None  # AI_PROVIDER unset by default


class TestGetAdminAIService:
    """@brief Wiring of get_admin_ai_service (IP resolution, audit binding)."""

    @staticmethod
    def _request(headers: dict[str, str], host: str | None):
        req = MagicMock()
        req.headers = headers
        req.client = MagicMock(host=host) if host else None
        return req

    def _build(self, headers: dict[str, str], host: str | None):
        from app.core.dependencies import get_admin_ai_service

        user = MagicMock()
        user.id = uuid.uuid4()
        with patch("app.core.valkey.get_pool", return_value=MagicMock()):
            svc = get_admin_ai_service(
                self._request(headers, host),
                user=user,
                db=AsyncMock(),
                settings=Settings(SECRET_KEY="x", AI_PROVIDER=""),
            )
        return svc, user

    def test_wires_repos_and_actor_with_forwarded_ip(self):
        from app.repositories.audit_repo import AuditRepository
        from app.repositories.community_repo import CommunityRepository

        svc, user = self._build({"x-forwarded-for": "9.9.9.9, 10.0.0.1"}, "10.0.0.1")
        assert isinstance(svc._communities, CommunityRepository)
        assert isinstance(svc._audit, AuditRepository)
        assert svc._actor_id == user.id
        assert svc._ip == "9.9.9.9"
        assert svc._provider_factory() is None  # AI_PROVIDER unset

    def test_falls_back_to_client_host(self):
        svc, _ = self._build({}, "10.0.0.1")
        assert svc._ip == "10.0.0.1"

    def test_no_ip_when_no_client(self):
        svc, _ = self._build({}, None)
        assert svc._ip is None
