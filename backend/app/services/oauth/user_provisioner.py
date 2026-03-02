"""
@file user_provisioner.py
@brief Provisions or links users from OAuth/OIDC authentication results.

Creates new users, links existing users by email, or updates existing
OAuth links with new role/avatar data.
"""

from __future__ import annotations

import re
import secrets
import uuid
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.oauth_provider import OAuthProvider
from app.models.user import User
from app.models.user_oauth_link import UserOAuthLink
from app.repositories.oauth_repo import UserOAuthLinkRepository
from app.repositories.user_repo import UserRepository


@dataclass
class OAuthAuthResult:
    """
    @brief Common output from an OAuth authentication flow.

    Contains the standard claims extracted from id_token or userinfo.
    """

    sub: str
    email: str | None = None
    display_name: str | None = None
    avatar_url: str | None = None
    groups: list[str] = field(default_factory=list)
    raw_claims: dict = field(default_factory=dict)


def _derive_username(name: str | None, email: str | None) -> str:
    """
    @brief Derive a URL-safe username from name or email.

    @param name Display name from IdP.
    @param email Email from IdP.
    @return Clean username, max 30 chars, or user_<hex> fallback.
    """
    base = name or (email.split("@")[0] if email else "")
    clean = re.sub(r"[^a-zA-Z0-9_-]", "", base.replace(" ", "_"))
    return clean[:30] or f"user_{secrets.token_hex(4)}"


class UserProvisioner:
    """
    @brief Provisions or links users from OAuth auth results.

    @param session Async DB session.
    @param community_id Community scope for new users.
    """

    def __init__(self, session: AsyncSession, community_id: uuid.UUID) -> None:
        self._session = session
        self._community_id = community_id
        self._user_repo = UserRepository(session)
        self._link_repo = UserOAuthLinkRepository(session)

    async def provision_user(
        self,
        auth_result: OAuthAuthResult,
        provider: OAuthProvider,
        role: str,
    ) -> User:
        """
        @brief Provision or link a user from OAuth auth result.

        1. Look up UserOAuthLink by (provider.id, auth_result.sub)
        2. If found: fetch user, update role/avatar if changed, return
        3. If not: look up user by email
        4. If found by email: create UserOAuthLink, update avatar, return
        5. If not found: derive username, create User + UserOAuthLink, return

        @param auth_result OAuth claims (sub, email, name, avatar, etc.).
        @param provider OAuth provider config.
        @param role Resolved role from group mapping.
        @return The User instance (existing or newly created).
        """
        link = await self._link_repo.find_by_provider_and_sub(provider.id, auth_result.sub)
        if link:
            user = await self._user_repo.get_by_id(link.user_id, self._community_id)
            if not user:
                raise ValueError("OAuth link references missing user")
            updates: dict = {}
            if user.role != role:
                updates["role"] = role
            if auth_result.avatar_url is not None and user.avatar_url != auth_result.avatar_url:
                updates["avatar_url"] = auth_result.avatar_url
            if updates:
                await self._user_repo.update(user, updates)
            return user

        user = None
        if auth_result.email:
            user = await self._user_repo.find_by_email(auth_result.email)
        if user:
            new_link = UserOAuthLink(
                user_id=user.id,
                provider_id=provider.id,
                sub=auth_result.sub,
                email_from_provider=auth_result.email,
                avatar_url=auth_result.avatar_url,
                raw_claims=auth_result.raw_claims,
            )
            await self._link_repo.create(new_link)
            if auth_result.avatar_url is not None:
                await self._user_repo.update(user, {"avatar_url": auth_result.avatar_url})
            return user

        username = _derive_username(auth_result.display_name, auth_result.email)
        while await self._user_repo.find_by_username(username):
            username = f"user_{secrets.token_hex(4)}"
        new_user = User(
            community_id=self._community_id,
            email=auth_result.email or f"{auth_result.sub}@oauth.local",
            username=username,
            display_name=auth_result.display_name or username,
            role=role,
            email_verified=True,
            avatar_url=auth_result.avatar_url,
        )
        new_user = await self._user_repo.create(new_user)
        new_link = UserOAuthLink(
            user_id=new_user.id,
            provider_id=provider.id,
            sub=auth_result.sub,
            email_from_provider=auth_result.email,
            avatar_url=auth_result.avatar_url,
            raw_claims=auth_result.raw_claims,
        )
        await self._link_repo.create(new_link)
        return new_user
