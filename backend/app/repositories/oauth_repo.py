"""
@file oauth_repo.py
@brief Repositories for OAuth providers and user OAuth links.

OAuthProviderRepository: per-community OAuth config lookups.
UserOAuthLinkRepository: user-to-provider identity links.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.oauth_provider import OAuthProvider
from app.models.user_oauth_link import UserOAuthLink
from app.repositories.base import BaseRepository


class OAuthProviderRepository(BaseRepository[OAuthProvider]):
    """
    @brief Async repository for OAuth provider configuration.

    Provides find_by_slug, list_enabled, and find_seeded queries.
    """

    model = OAuthProvider

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def find_by_slug(
        self,
        community_id: uuid.UUID,
        slug: str,
    ) -> OAuthProvider | None:
        """
        @brief Look up a provider by community and slug.

        @param community_id Community scope.
        @param slug Provider slug (e.g. "google").
        @return The OAuthProvider or None.
        """
        stmt = (
            self._base_query()
            .where(OAuthProvider.community_id == community_id)
            .where(OAuthProvider.slug == slug)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_enabled(
        self,
        community_id: uuid.UUID,
    ) -> list[OAuthProvider]:
        """
        @brief List enabled OAuth providers for a community.

        @param community_id Community scope.
        @return List of enabled OAuthProvider instances.
        """
        stmt = (
            self._base_query()
            .where(OAuthProvider.community_id == community_id)
            .where(OAuthProvider.enabled.is_(True))
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def find_seeded(
        self,
        community_id: uuid.UUID,
    ) -> OAuthProvider | None:
        """
        @brief Find the provider seeded from environment (if any).

        @param community_id Community scope.
        @return The seeded OAuthProvider or None.
        """
        stmt = (
            self._base_query()
            .where(OAuthProvider.community_id == community_id)
            .where(OAuthProvider.seeded_from_env.is_(True))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()


class UserOAuthLinkRepository(BaseRepository[UserOAuthLink]):
    """
    @brief Async repository for user OAuth identity links.

    Provides find_by_provider_and_sub and find_links_for_user.
    """

    model = UserOAuthLink

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def find_by_provider_and_sub(
        self,
        provider_id: uuid.UUID,
        sub: str,
    ) -> UserOAuthLink | None:
        """
        @brief Look up a link by provider and subject identifier.

        @param provider_id OAuth provider UUID.
        @param sub The ``sub`` claim from the provider.
        @return The UserOAuthLink or None.
        """
        stmt = (
            self._base_query()
            .where(UserOAuthLink.provider_id == provider_id)
            .where(UserOAuthLink.sub == sub)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_links_for_user(
        self,
        user_id: uuid.UUID,
    ) -> list[UserOAuthLink]:
        """
        @brief List all OAuth links for a user.

        @param user_id User UUID.
        @return List of UserOAuthLink instances.
        """
        stmt = self._base_query().where(UserOAuthLink.user_id == user_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
