"""
@file test_oauth_repo.py
@brief Unit tests for OAuthProviderRepository and UserOAuthLinkRepository.

Tests verify OAuth query methods using mocked AsyncSession.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.oauth_provider import OAuthProvider
from app.models.user_oauth_link import UserOAuthLink
from app.repositories.oauth_repo import OAuthProviderRepository, UserOAuthLinkRepository

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
PROVIDER_ID = uuid.uuid4()
USER_ID = uuid.uuid4()


def _make_session() -> AsyncMock:
    """@brief Create a mock AsyncSession with execute stub."""
    session = AsyncMock()
    session.execute = AsyncMock()
    return session


class TestOAuthProviderRepositoryFindBySlug:
    """@brief Tests for OAuthProviderRepository.find_by_slug()."""

    @pytest.mark.asyncio
    async def test_returns_provider_when_found(self):
        """find_by_slug should return OAuthProvider when one exists."""
        provider = MagicMock(spec=OAuthProvider)
        session = _make_session()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = provider
        session.execute.return_value = mock_result

        repo = OAuthProviderRepository(session)
        result = await repo.find_by_slug(COMMUNITY_ID, "google")

        assert result is provider
        session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        """find_by_slug should return None when no provider matches."""
        session = _make_session()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute.return_value = mock_result

        repo = OAuthProviderRepository(session)
        result = await repo.find_by_slug(COMMUNITY_ID, "nonexistent")

        assert result is None


class TestOAuthProviderRepositoryListEnabled:
    """@brief Tests for OAuthProviderRepository.list_enabled()."""

    @pytest.mark.asyncio
    async def test_returns_list_of_enabled_providers(self):
        """list_enabled should return enabled providers for the community."""
        p1 = MagicMock(spec=OAuthProvider)
        p2 = MagicMock(spec=OAuthProvider)
        session = _make_session()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [p1, p2]
        session.execute.return_value = mock_result

        repo = OAuthProviderRepository(session)
        result = await repo.list_enabled(COMMUNITY_ID)

        assert result == [p1, p2]
        session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_none(self):
        """list_enabled should return empty list when no enabled providers."""
        session = _make_session()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        session.execute.return_value = mock_result

        repo = OAuthProviderRepository(session)
        result = await repo.list_enabled(COMMUNITY_ID)

        assert result == []


class TestOAuthProviderRepositoryFindSeeded:
    """@brief Tests for OAuthProviderRepository.find_seeded()."""

    @pytest.mark.asyncio
    async def test_returns_seeded_provider_when_found(self):
        """find_seeded should return provider when one is seeded from env."""
        provider = MagicMock(spec=OAuthProvider)
        session = _make_session()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = provider
        session.execute.return_value = mock_result

        repo = OAuthProviderRepository(session)
        result = await repo.find_seeded(COMMUNITY_ID)

        assert result is provider

    @pytest.mark.asyncio
    async def test_returns_none_when_no_seeded(self):
        """find_seeded should return None when no seeded provider exists."""
        session = _make_session()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute.return_value = mock_result

        repo = OAuthProviderRepository(session)
        result = await repo.find_seeded(COMMUNITY_ID)

        assert result is None


class TestUserOAuthLinkRepositoryFindByProviderAndSub:
    """@brief Tests for UserOAuthLinkRepository.find_by_provider_and_sub()."""

    @pytest.mark.asyncio
    async def test_returns_link_when_found(self):
        """find_by_provider_and_sub should return UserOAuthLink when exists."""
        link = MagicMock(spec=UserOAuthLink)
        session = _make_session()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = link
        session.execute.return_value = mock_result

        repo = UserOAuthLinkRepository(session)
        result = await repo.find_by_provider_and_sub(PROVIDER_ID, "sub-123")

        assert result is link

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        """find_by_provider_and_sub should return None when no link exists."""
        session = _make_session()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute.return_value = mock_result

        repo = UserOAuthLinkRepository(session)
        result = await repo.find_by_provider_and_sub(PROVIDER_ID, "unknown")

        assert result is None


class TestUserOAuthLinkRepositoryFindLinksForUser:
    """@brief Tests for UserOAuthLinkRepository.find_links_for_user()."""

    @pytest.mark.asyncio
    async def test_returns_list_of_links(self):
        """find_links_for_user should return all links for the user."""
        link1 = MagicMock(spec=UserOAuthLink)
        link2 = MagicMock(spec=UserOAuthLink)
        session = _make_session()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [link1, link2]
        session.execute.return_value = mock_result

        repo = UserOAuthLinkRepository(session)
        result = await repo.find_links_for_user(USER_ID)

        assert result == [link1, link2]

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_links(self):
        """find_links_for_user should return empty list when user has no links."""
        session = _make_session()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        session.execute.return_value = mock_result

        repo = UserOAuthLinkRepository(session)
        result = await repo.find_links_for_user(USER_ID)

        assert result == []
