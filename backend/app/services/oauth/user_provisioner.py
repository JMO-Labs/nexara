"""
@file user_provisioner.py
@brief Creates or updates users from OAuth claims.

Defines OAuthAuthResult and UserProvisioner for linking OAuth identities
to users, creating new users when needed.
"""

from __future__ import annotations

import re
import secrets
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError
from app.models.user import User
from app.models.user_oauth_link import UserOAuthLink
from app.plugins.hooks import HookRegistry
from app.repositories.calendar_repo import CalendarRepository
from app.repositories.oauth_repo import UserOAuthLinkRepository
from app.repositories.user_repo import UserRepository

if TYPE_CHECKING:
    from app.models.oauth_provider import OAuthProvider


@dataclass
class OAuthAuthResult:
    """@brief Extracted auth data from OIDC claims."""

    sub: str
    email: str | None
    display_name: str | None = None
    avatar_url: str | None = None
    groups: list[str] | None = None
    email_verified: bool = False

    def __post_init__(self) -> None:
        """@brief Ensure groups is a list."""
        if self.groups is None:
            self.groups = []


def _derive_username(display_name: str | None, email: str | None) -> str:
    """
    @brief Derive a URL-safe username from display_name or email.

    @param display_name Display name (preferred). Spaces become underscores.
    @param email Email fallback; uses part before @.
    @return Cleaned username, max 30 chars, or "user_" + 8 hex chars if both None.
    """
    if display_name:
        base = display_name.replace(" ", "_")
        clean = re.sub(r"[^a-zA-Z0-9_-]", "", base)
        if clean:
            return clean[:30]
    if email:
        base = email.split("@")[0]
        clean = re.sub(r"[^a-zA-Z0-9_-]", "", base)
        if clean:
            return clean[:30]
    return "user_" + secrets.token_hex(4)


class UserProvisioner:
    """
    @brief Provisions users from OAuth authentication results.

    Creates new users or links existing ones via UserOAuthLink.
    """

    def __init__(
        self,
        db: AsyncSession,
        community_id: uuid.UUID,
    ) -> None:
        """
        @brief Initialize the provisioner.

        @param db Async database session.
        @param community_id Community to provision users into.
        """
        self._db = db
        self._community_id = community_id
        self._link_repo = UserOAuthLinkRepository(db)
        self._user_repo = UserRepository(db)

    async def provision_user(
        self,
        auth_result: OAuthAuthResult,
        provider: OAuthProvider,
        role: str,
    ) -> User:
        """
        @brief Create or update a user from OAuth claims.

        Looks up by provider+sub via UserOAuthLink first, then by email
        (case-insensitive, requires email_verified; else AuthenticationError).
        Creates UserOAuthLink for new users.

        Role handling:
        - On first login (new user or first link), the resolved role is applied.
        - On subsequent logins, the role is only synced when the provider has
          explicit group_mappings configured, so that manually assigned roles
          (e.g. admin) are preserved when no group mapping is in use.

        @param auth_result Extracted claims from token.
        @param provider OAuth provider configuration.
        @param role Resolved role (from group mapping or default).
        @return The user (created or updated).
        """
        has_group_mappings = bool(provider.group_mappings)

        link = await self._link_repo.find_by_provider_and_sub(provider.id, auth_result.sub)
        if link:
            user = await self._user_repo.get_by_id(link.user_id)
            if user:
                updates: dict[str, object] = {}
                if has_group_mappings and user.role != role:
                    updates["role"] = role
                if auth_result.avatar_url and auth_result.avatar_url != link.avatar_url:
                    updates["avatar_url"] = auth_result.avatar_url
                if updates:
                    await self._user_repo.update(user, updates)
                # Keep the link's provider-side data fresh.
                link_updates: dict[str, object] = {}
                if auth_result.email and auth_result.email != link.email_from_provider:
                    link_updates["email_from_provider"] = auth_result.email
                if auth_result.avatar_url and auth_result.avatar_url != link.avatar_url:
                    link_updates["avatar_url"] = auth_result.avatar_url
                if link_updates:
                    await self._link_repo.update(link, link_updates)
                return user

        # No link yet: only a provider-verified email may create or link an account.
        if not auth_result.email or not auth_result.email_verified:
            raise AuthenticationError(message="Email not verified by identity provider")
        email = auth_result.email.strip().lower()

        user = await self._user_repo.find_by_email(email)
        if user:
            # First OAuth link for existing user — only set role when
            # the provider actively maps groups.
            if has_group_mappings and user.role != role:
                await self._user_repo.update(user, {"role": role})
            new_link = UserOAuthLink(
                user_id=user.id,
                provider_id=provider.id,
                sub=auth_result.sub,
                email_from_provider=auth_result.email,
                avatar_url=auth_result.avatar_url,
            )
            await self._link_repo.create(new_link)
            return user

        username = _derive_username(auth_result.display_name, auth_result.email)
        user = User(
            community_id=self._community_id,
            email=email,
            username=username,
            display_name=auth_result.display_name or username,
            role=role,
            email_verified=True,
            avatar_url=auth_result.avatar_url,
        )
        user = await self._user_repo.create(user)
        new_link = UserOAuthLink(
            user_id=user.id,
            provider_id=provider.id,
            sub=auth_result.sub,
            email_from_provider=auth_result.email,
            avatar_url=auth_result.avatar_url,
        )
        await self._link_repo.create(new_link)
        await CalendarRepository(self._db).ensure_personal(self._community_id, user.id)
        await HookRegistry.emit(
            "on_user_joined",
            community_id=self._community_id,
            session=self._db,
            user_id=user.id,
        )
        return user
