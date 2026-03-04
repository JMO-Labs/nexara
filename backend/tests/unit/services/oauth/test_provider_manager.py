"""
@file test_provider_manager.py
@brief Unit tests for OAuth provider manager with caching and env seeding.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.services.oauth.provider_manager as pm
from app.services.oauth.provider_manager import ProviderManager


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear module-level provider cache between tests."""
    pm._provider_cache.clear()
    yield
    pm._provider_cache.clear()


class TestGetProvider:
    """@brief Tests for ProviderManager.get_provider."""

    @pytest.mark.asyncio
    async def test_returns_provider_from_repo(self):
        """get_provider returns provider from repo."""
        mock_provider = MagicMock()
        mock_provider.slug = "oidc"
        mock_repo = AsyncMock()
        mock_repo.find_by_slug = AsyncMock(return_value=mock_provider)
        mock_session = AsyncMock()

        with patch.object(pm, "OAuthProviderRepository", return_value=mock_repo):
            manager = ProviderManager(mock_session)
            community_id = uuid.uuid4()
            result = await manager.get_provider(community_id, "oidc")

        assert result is mock_provider
        mock_repo.find_by_slug.assert_called_once_with(community_id, "oidc")

    @pytest.mark.asyncio
    async def test_returns_cached_provider_on_second_call(self):
        """get_provider returns cached provider on second call."""
        mock_provider = MagicMock()
        mock_provider.slug = "oidc"
        mock_repo = AsyncMock()
        mock_repo.find_by_slug = AsyncMock(return_value=mock_provider)
        mock_session = AsyncMock()

        with patch.object(pm, "OAuthProviderRepository", return_value=mock_repo):
            manager = ProviderManager(mock_session)
            community_id = uuid.uuid4()
            first = await manager.get_provider(community_id, "oidc")
            second = await manager.get_provider(community_id, "oidc")

        assert first is second
        mock_repo.find_by_slug.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_expires_after_ttl(self):
        """get_provider cache expires after TTL."""
        mock_provider = MagicMock()
        mock_provider.slug = "oidc"
        mock_repo = AsyncMock()
        mock_repo.find_by_slug = AsyncMock(return_value=mock_provider)
        mock_session = AsyncMock()

        with patch.object(pm, "OAuthProviderRepository", return_value=mock_repo):
            with patch.object(pm, "CACHE_TTL", 0):
                manager = ProviderManager(mock_session)
                community_id = uuid.uuid4()
                await manager.get_provider(community_id, "oidc")
                await manager.get_provider(community_id, "oidc")

        assert mock_repo.find_by_slug.call_count == 2


class TestGetEnabledProviders:
    """@brief Tests for ProviderManager.get_enabled_providers."""

    @pytest.mark.asyncio
    async def test_delegates_to_repo(self):
        """get_enabled_providers delegates to repo."""
        mock_providers = [MagicMock(), MagicMock()]
        mock_repo = AsyncMock()
        mock_repo.list_enabled = AsyncMock(return_value=mock_providers)
        mock_session = AsyncMock()

        with patch.object(pm, "OAuthProviderRepository", return_value=mock_repo):
            manager = ProviderManager(mock_session)
            community_id = uuid.uuid4()
            result = await manager.get_enabled_providers(community_id)

        assert result == mock_providers
        mock_repo.list_enabled.assert_called_once_with(community_id)


class TestInvalidateCache:
    """@brief Tests for ProviderManager.invalidate_cache."""

    @pytest.mark.asyncio
    async def test_clears_module_cache(self):
        """invalidate_cache clears the module cache."""
        mock_provider = MagicMock()
        mock_repo = AsyncMock()
        mock_repo.find_by_slug = AsyncMock(return_value=mock_provider)
        mock_session = AsyncMock()

        with patch.object(pm, "OAuthProviderRepository", return_value=mock_repo):
            manager = ProviderManager(mock_session)
            community_id = uuid.uuid4()
            await manager.get_provider(community_id, "oidc")
            assert len(pm._provider_cache) > 0
            manager.invalidate_cache()
            assert len(pm._provider_cache) == 0


class TestSeedFromEnv:
    """@brief Tests for ProviderManager.seed_from_env."""

    @pytest.mark.asyncio
    async def test_skips_when_oidc_issuer_empty(self):
        """seed_from_env skips when OIDC_ISSUER is empty."""
        mock_settings = MagicMock()
        mock_settings.OIDC_ISSUER = ""
        mock_settings.SECRET_KEY = "secret"
        mock_repo = AsyncMock()
        mock_session = AsyncMock()

        with patch.object(pm, "OAuthProviderRepository", return_value=mock_repo):
            manager = ProviderManager(mock_session)
            community_id = uuid.uuid4()
            result = await manager.seed_from_env(mock_settings, community_id)

        assert result is None
        mock_repo.find_seeded.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_when_provider_already_seeded(self):
        """seed_from_env skips when provider already seeded."""
        mock_settings = MagicMock()
        mock_settings.OIDC_ISSUER = "https://idp.example.com"
        mock_settings.SECRET_KEY = "secret"
        mock_existing = MagicMock()
        mock_repo = AsyncMock()
        mock_repo.find_seeded = AsyncMock(return_value=mock_existing)
        mock_session = AsyncMock()

        with patch.object(pm, "OAuthProviderRepository", return_value=mock_repo):
            manager = ProviderManager(mock_session)
            community_id = uuid.uuid4()
            result = await manager.seed_from_env(mock_settings, community_id)

        assert result is None
        mock_repo.find_seeded.assert_called_once_with(community_id)

    @pytest.mark.asyncio
    async def test_creates_provider_when_none_exists(self):
        """seed_from_env creates provider when none exists."""
        mock_settings = MagicMock()
        mock_settings.OIDC_ISSUER = "https://idp.example.com"
        mock_settings.SECRET_KEY = "secret"
        mock_settings.OIDC_CLIENT_ID = "client"
        mock_settings.OIDC_CLIENT_SECRET = "client-secret"
        mock_settings.OIDC_SCOPES = "openid profile email"

        mock_created = MagicMock()
        mock_repo = AsyncMock()
        mock_repo.find_seeded = AsyncMock(return_value=None)
        mock_repo.create = AsyncMock(return_value=mock_created)
        mock_session = AsyncMock()

        endpoints = {
            "authorization_endpoint": "https://idp.example.com/authorize",
            "token_endpoint": "https://idp.example.com/token",
            "userinfo_endpoint": "https://idp.example.com/userinfo",
            "jwks_uri": "https://idp.example.com/jwks",
        }

        with patch.object(pm, "OAuthProviderRepository", return_value=mock_repo):
            with patch.object(pm, "discover_endpoints", AsyncMock(return_value=endpoints)):
                with patch.object(pm, "encrypt_secret", return_value="encrypted"):
                    with patch.object(pm, "derive_fernet_key", return_value=b"key"):
                        manager = ProviderManager(mock_session)
                        community_id = uuid.uuid4()
                        result = await manager.seed_from_env(mock_settings, community_id)

        assert result is mock_created
        mock_repo.create.assert_called_once()
