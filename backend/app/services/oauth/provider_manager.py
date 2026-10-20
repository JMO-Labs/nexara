"""
@file provider_manager.py
@brief Caches and retrieves OAuth provider configuration.
"""

from __future__ import annotations

import time
import uuid
from typing import TYPE_CHECKING, Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import derive_fernet_key, encrypt_secret
from app.models.oauth_provider import OAuthProvider
from app.repositories.oauth_repo import OAuthProviderRepository

if TYPE_CHECKING:
    pass

CACHE_TTL: float = 300.0
"""@brief Seconds to cache provider lookups."""

_provider_cache: dict[tuple[uuid.UUID, str], tuple[OAuthProvider, float]] = {}
"""@brief Module-level cache: (community_id, slug) -> (provider, expires_at)."""


async def discover_endpoints(issuer: str) -> dict[str, str]:
    """
    @brief Fetch OIDC discovery endpoints from issuer.

    @param issuer OIDC issuer URL (e.g. https://idp.example.com).
    @return Dict with authorization_endpoint, token_endpoint, etc.
    """
    url = issuer.rstrip("/") + "/.well-known/openid-configuration"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()
    return {
        "authorization_endpoint": data.get("authorization_endpoint", ""),
        "token_endpoint": data.get("token_endpoint", ""),
        "userinfo_endpoint": data.get("userinfo_endpoint", ""),
        "jwks_uri": data.get("jwks_uri", ""),
    }


class ProviderManager:
    """
    @brief Manages OAuth provider lookup with optional in-memory cache.

    @param db Async SQLAlchemy session.
    """

    def __init__(self, db: AsyncSession) -> None:
        """
        @brief Initialize the provider manager.

        @param db Async database session.
        """
        self._session = db
        self._repo = OAuthProviderRepository(db)

    async def get_provider(
        self,
        community_id: uuid.UUID,
        slug: str,
    ) -> OAuthProvider | None:
        """
        @brief Fetch an OAuth provider by community and slug.

        Uses module-level cache with TTL; call invalidate_cache() after updates.

        @param community_id Community UUID.
        @param slug Provider slug (e.g. "google", "keycloak").
        @return The provider or None.
        """
        key = (community_id, slug)
        now = time.monotonic()
        if key in _provider_cache:
            cached_provider, expires_at = _provider_cache[key]
            if now < expires_at:
                return cached_provider
            del _provider_cache[key]

        provider = await self._repo.find_by_slug(community_id, slug)
        if provider is not None:
            _provider_cache[key] = (provider, now + CACHE_TTL)
            return provider
        return None

    async def get_enabled_providers(
        self,
        community_id: uuid.UUID,
    ) -> list[OAuthProvider]:
        """
        @brief List enabled OAuth providers for a community.

        @param community_id Community UUID.
        @return List of enabled providers.
        """
        return await self._repo.list_enabled(community_id)

    def invalidate_cache(self) -> None:
        """@brief Clear the module-level provider cache."""
        _provider_cache.clear()

    async def seed_from_env(
        self,
        settings: Any,
        community_id: uuid.UUID,
    ) -> OAuthProvider | None:
        """
        @brief Seed OAuth provider from OIDC_* environment settings.

        Skips when OIDC_ISSUER is empty or provider already seeded.

        @param settings Settings object with OIDC_*, SECRET_KEY.
        @param community_id Community to seed.
        @return Created provider or None if skipped.
        """
        if (
            not getattr(settings, "OIDC_ISSUER", "")
            or not str(getattr(settings, "OIDC_ISSUER", "")).strip()
        ):
            return None

        existing = await self._repo.find_seeded(community_id)
        if existing is not None:
            return None

        issuer = str(settings.OIDC_ISSUER).rstrip("/")
        endpoints = await discover_endpoints(issuer)
        key = derive_fernet_key(settings.SECRET_KEY)
        client_secret_enc = encrypt_secret(getattr(settings, "OIDC_CLIENT_SECRET", "") or "", key)

        provider = OAuthProvider(
            community_id=community_id,
            slug="oidc",
            display_name="OIDC",
            client_id=getattr(settings, "OIDC_CLIENT_ID", "") or "",
            client_secret_encrypted=client_secret_enc,
            scopes=getattr(settings, "OIDC_SCOPES", "openid profile email") or "",
            authorization_endpoint=endpoints.get("authorization_endpoint"),
            token_endpoint=endpoints.get("token_endpoint"),
            userinfo_endpoint=endpoints.get("userinfo_endpoint"),
            jwks_uri=endpoints.get("jwks_uri"),
            seeded_from_env=True,
        )
        return await self._repo.create(provider)
