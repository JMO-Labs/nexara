"""
@file test_provider_manager.py
@brief Tests for ProviderManager: caching, seeding, invalidation.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.config import Settings
from app.models.oauth_provider import OAuthProvider
from app.services.oauth.provider_manager import ProviderManager


def _make_provider(
    provider_id: uuid.UUID | None = None,
    community_id: uuid.UUID | None = None,
    slug: str = "oidc",
) -> OAuthProvider:
    """@brief Create a mock OAuthProvider."""
    p = MagicMock(spec=OAuthProvider)
    p.id = provider_id or uuid.uuid4()
    p.community_id = community_id or uuid.UUID("00000000-0000-0000-0000-000000000001")
    p.slug = slug
    p.issuer = "https://idp.example.com"
    return p


class TestProviderManagerGetProvider:
    """@brief get_provider returns provider from repo."""

    @pytest.mark.asyncio
    async def test_returns_provider_from_repo(self):
        """@brief get_provider(community_id, slug) returns provider from repo."""
        community_id = uuid.uuid4()
        provider = _make_provider(community_id=community_id, slug="google")

        provider_repo = AsyncMock()
        provider_repo.find_by_slug = AsyncMock(return_value=provider)

        session = AsyncMock()
        manager = ProviderManager(session)
        manager._provider_repo = provider_repo

        result = await manager.get_provider(community_id, "google")

        assert result == provider
        provider_repo.find_by_slug.assert_called_once_with(community_id, "google")

    @pytest.mark.asyncio
    async def test_second_call_uses_cache(self):
        """@brief Second get_provider call does not hit repo (cache hit)."""
        community_id = uuid.uuid4()
        provider = _make_provider(community_id=community_id, slug="oidc")

        provider_repo = AsyncMock()
        provider_repo.find_by_slug = AsyncMock(return_value=provider)

        session = AsyncMock()
        manager = ProviderManager(session)
        manager._provider_repo = provider_repo

        await manager.get_provider(community_id, "oidc")
        await manager.get_provider(community_id, "oidc")

        assert provider_repo.find_by_slug.call_count == 1


class TestProviderManagerGetEnabledProviders:
    """@brief get_enabled_providers returns list from repo."""

    @pytest.mark.asyncio
    async def test_returns_list_from_repo(self):
        """@brief get_enabled_providers(community_id) returns list from repo."""
        community_id = uuid.uuid4()
        providers = [_make_provider(community_id=community_id, slug="a")]

        provider_repo = AsyncMock()
        provider_repo.list_enabled = AsyncMock(return_value=providers)

        session = AsyncMock()
        manager = ProviderManager(session)
        manager._provider_repo = provider_repo

        result = await manager.get_enabled_providers(community_id)

        assert result == providers
        provider_repo.list_enabled.assert_called_once_with(community_id)


class TestProviderManagerInvalidateCache:
    """@brief invalidate_cache clears cache."""

    @pytest.mark.asyncio
    async def test_invalidate_clears_cache_next_get_hits_repo(self):
        """@brief invalidate_cache() clears cache; next get_provider hits repo."""
        community_id = uuid.uuid4()
        provider = _make_provider(community_id=community_id, slug="oidc")

        provider_repo = AsyncMock()
        provider_repo.find_by_slug = AsyncMock(return_value=provider)

        session = AsyncMock()
        manager = ProviderManager(session)
        manager._provider_repo = provider_repo

        await manager.get_provider(community_id, "oidc")
        manager.invalidate_cache()
        await manager.get_provider(community_id, "oidc")

        assert provider_repo.find_by_slug.call_count == 2


class TestProviderManagerSeedFromEnv:
    """@brief seed_from_env creates provider when OIDC_ISSUER set."""

    @pytest.mark.asyncio
    async def test_creates_provider_when_issuer_set_and_no_seeded(self):
        """@brief OIDC_ISSUER set, no seeded provider -> creates one."""
        community_id = uuid.uuid4()
        settings = Settings(
            OIDC_ISSUER="https://idp.example.com",
            OIDC_CLIENT_ID="client",
            OIDC_CLIENT_SECRET="secret",
            OIDC_SCOPES="openid profile email",
        )

        provider_repo = AsyncMock()
        provider_repo.find_seeded = AsyncMock(return_value=None)
        created_provider = _make_provider(community_id=community_id)
        provider_repo.create = AsyncMock(return_value=created_provider)

        session = AsyncMock()
        manager = ProviderManager(session)
        manager._provider_repo = provider_repo

        with (
            patch(
                "app.services.oauth.provider_manager.discover_endpoints",
                new_callable=AsyncMock,
                return_value={
                    "authorization_endpoint": "https://idp.example.com/authorize",
                    "token_endpoint": "https://idp.example.com/token",
                    "userinfo_endpoint": "https://idp.example.com/userinfo",
                    "jwks_uri": "https://idp.example.com/jwks",
                    "end_session_endpoint": None,
                },
            ),
            patch("app.services.oauth.provider_manager.encrypt_secret", return_value="encrypted"),
        ):
            await manager.seed_from_env(settings, community_id)

        provider_repo.find_seeded.assert_called_once_with(community_id)
        provider_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_skips_when_seeded_exists(self):
        """@brief Skips when find_seeded returns non-None."""
        community_id = uuid.uuid4()
        settings = Settings(
            OIDC_ISSUER="https://idp.example.com",
            OIDC_CLIENT_ID="client",
            OIDC_CLIENT_SECRET="secret",
        )
        existing_seeded = _make_provider(community_id=community_id)

        provider_repo = AsyncMock()
        provider_repo.find_seeded = AsyncMock(return_value=existing_seeded)

        session = AsyncMock()
        manager = ProviderManager(session)
        manager._provider_repo = provider_repo

        await manager.seed_from_env(settings, community_id)

        provider_repo.find_seeded.assert_called_once_with(community_id)
        provider_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_when_issuer_empty(self):
        """@brief Skips when OIDC_ISSUER is empty."""
        community_id = uuid.uuid4()
        settings = Settings(OIDC_ISSUER="", OIDC_CLIENT_ID="", OIDC_CLIENT_SECRET="")

        provider_repo = AsyncMock()
        provider_repo.find_seeded = AsyncMock(return_value=None)

        session = AsyncMock()
        manager = ProviderManager(session)
        manager._provider_repo = provider_repo

        await manager.seed_from_env(settings, community_id)

        provider_repo.find_seeded.assert_not_called()
        provider_repo.create.assert_not_called()
