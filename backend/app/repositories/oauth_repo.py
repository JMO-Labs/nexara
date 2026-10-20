"""
@file oauth_repo.py
@brief Repositories for OAuthProvider and UserOAuthLink models.

Provides OAuthProviderRepository and UserOAuthLinkRepository with
community-scoped queries and soft-delete filtering.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.oauth_provider import OAuthProvider
from app.models.user_oauth_link import UserOAuthLink
from app.repositories.base import BaseRepository


class OAuthProviderRepository(BaseRepository[OAuthProvider]):
    """
    @brief Repository for OAuth provider configuration.

    Supports find_by_slug, list_enabled, find_seeded, plus inherited
    list, create, get_by_id, update, soft_delete.
    """

    model = OAuthProvider

    def __init__(self, session: AsyncSession) -> None:
        """
        @brief Initialize the repository.

        @param session Async SQLAlchemy session.
        """
        super().__init__(session)

    async def find_by_slug(
        self,
        community_id: uuid.UUID,
        slug: str,
    ) -> OAuthProvider | None:
        """
        @brief Fetch a provider by community and slug.

        @param community_id Community scope.
        @param slug Provider slug (e.g. "google").
        @return The provider or None.
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
        @brief List enabled providers for a community.

        @param community_id Community scope.
        @return List of enabled providers.
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
        @brief Fetch the seeded-from-env provider for a community.

        @param community_id Community scope.
        @return The seeded provider or None.
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
    @brief Repository for UserOAuthLink (user-to-provider links).

    Supports find_by_provider_and_sub, find_links_for_user, create.
    """

    model = UserOAuthLink

    def __init__(self, session: AsyncSession) -> None:
        """
        @brief Initialize the repository.

        @param session Async SQLAlchemy session.
        """
        super().__init__(session)

    async def find_by_provider_and_sub(
        self,
        provider_id: uuid.UUID,
        sub: str,
    ) -> UserOAuthLink | None:
        """
        @brief Find link by provider and subject claim.

        @param provider_id OAuth provider UUID.
        @param sub Subject claim from ID token.
        @return The link or None.
        """
        stmt = select(UserOAuthLink).where(
            UserOAuthLink.provider_id == provider_id,
            UserOAuthLink.sub == sub,
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
        @return List of UserOAuthLink.
        """
        stmt = select(UserOAuthLink).where(UserOAuthLink.user_id == user_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
