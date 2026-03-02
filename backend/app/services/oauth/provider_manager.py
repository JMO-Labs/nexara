"""
@file provider_manager.py
@brief OAuth provider lookup with in-memory caching and env-based seeding.

Caches provider lookups by (community_id, slug) with TTL. Supports
seeding a provider from OIDC_* environment variables.
"""

from __future__ import annotations

import time
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.encryption import derive_fernet_key, encrypt_secret
from app.models.oauth_provider import OAuthProvider
from app.repositories.oauth_repo import OAuthProviderRepository
from app.services.oauth.discovery import discover_endpoints

CACHE_TTL = 300
"""@brief Cache TTL in seconds for provider lookups."""

_provider_cache: dict[str, tuple[OAuthProvider, float]] = {}
"""@brief Module-level cache: key -> (provider, timestamp)."""


class ProviderManager:
    """
    @brief Manages OAuth provider lookups with caching and env seeding.

    @param session Async DB session.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._provider_repo = OAuthProviderRepository(session)

    async def get_provider(
        self,
        community_id: uuid.UUID,
        slug: str,
    ) -> OAuthProvider | None:
        """
        @brief Get a provider by community and slug (cached).

        @param community_id Community scope.
        @param slug Provider slug.
        @return OAuthProvider or None.
        """
        key = f"{community_id}:{slug}"
        now = time.monotonic()
        if key in _provider_cache:
            provider, ts = _provider_cache[key]
            if now - ts < CACHE_TTL:
                return provider
            del _provider_cache[key]
        provider = await self._provider_repo.find_by_slug(community_id, slug)
        if provider:
            _provider_cache[key] = (provider, now)
        return provider

    async def get_enabled_providers(
        self,
        community_id: uuid.UUID,
    ) -> list[OAuthProvider]:
        """
        @brief List enabled providers for a community (not cached).

        @param community_id Community scope.
        @return List of enabled OAuthProvider instances.
        """
        return await self._provider_repo.list_enabled(community_id)

    def invalidate_cache(self) -> None:
        """@brief Clear the provider cache."""
        _provider_cache.clear()

    async def seed_from_env(
        self,
        settings: Settings,
        community_id: uuid.UUID,
    ) -> OAuthProvider | None:
        """
        @brief Seed a provider from OIDC_* env vars if not already seeded.

        @param settings Application settings.
        @param community_id Community scope.
        @return The created provider or None if skipped.
        """
        if not settings.OIDC_ISSUER or not settings.OIDC_ISSUER.strip():
            return None
        existing = await self._provider_repo.find_seeded(community_id)
        if existing:
            return None
        endpoints = await discover_endpoints(settings.OIDC_ISSUER.strip())
        fernet_key = derive_fernet_key(settings.SECRET_KEY)
        encrypted_secret = encrypt_secret(settings.OIDC_CLIENT_SECRET, fernet_key)
        provider = OAuthProvider(
            community_id=community_id,
            slug="oidc",
            display_name="OIDC",
            provider_type="oidc",
            issuer=settings.OIDC_ISSUER.strip(),
            client_id=settings.OIDC_CLIENT_ID,
            client_secret_encrypted=encrypted_secret,
            scopes=settings.OIDC_SCOPES or "openid profile email groups",
            authorization_endpoint=endpoints.get("authorization_endpoint"),
            token_endpoint=endpoints.get("token_endpoint"),
            userinfo_endpoint=endpoints.get("userinfo_endpoint"),
            jwks_uri=endpoints.get("jwks_uri"),
            end_session_endpoint=endpoints.get("end_session_endpoint"),
            seeded_from_env=True,
        )
        provider = await self._provider_repo.create(provider)
        return provider
