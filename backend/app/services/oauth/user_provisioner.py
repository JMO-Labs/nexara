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
from typing import TYPE_CHECKING, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, SsoRefusedError
from app.models.user import User
from app.models.user_oauth_link import UserOAuthLink
from app.repositories.calendar_repo import CalendarRepository
from app.repositories.oauth_repo import UserOAuthLinkRepository
from app.repositories.subgroup_repo import SubgroupMemberRepository, SubgroupRepository
from app.repositories.token_repo import TokenRepository
from app.repositories.user_repo import UserRepository
from app.services.auth.policy import factor_methods
from app.services.oauth.group_mapper import (
    apply_subgroup_mappings,
    global_role_mappings,
    has_subgroup_rules,
    resolve_subgroup_mappings,
)
from app.services.oauth.profile_sync import audit_role_synced, sync_profile
from app.services.oauth.role_sync import audit_role_sync_skipped, can_change_role
from app.services.oauth.sso_rules import clean_username, evaluate_gates, unique_username

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
    username: str | None = None
    """@brief Value of the provider's username_claim (None when absent)."""

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


CREATE_ATTEMPTS = 5
"""@brief Bounded retries of the JIT insert when a username race is lost."""


class UserProvisioner:
    """
    @brief Provisions users from OAuth authentication results.

    Order: domain gate -> group gate -> find by (provider, sub) -> link by
    verified email -> create (only if auto_create_users) -> disabled check.
    Refusals raise SsoRefusedError; a refused returning user also loses all
    refresh tokens.
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
        self.pending_link: dict[str, Any] | None = None
        """@brief Link deferred until the existing account's local 2FA passes."""
        self._link_repo = UserOAuthLinkRepository(db)
        self._user_repo = UserRepository(db)

    async def _refuse(self, code: str, user_id: uuid.UUID | None = None) -> SsoRefusedError:
        """@brief Build a refusal; a known (linked) user is signed out everywhere."""
        if user_id is not None:
            await TokenRepository(self._db).revoke_all_for_user(user_id)
        return SsoRefusedError(code, user_id)

    async def _sync_profile(
        self, user: User, auth_result: OAuthAuthResult, provider: OAuthProvider
    ) -> None:
        """@brief Profile sync when the provider enables it."""
        if provider.sync_profile:
            await sync_profile(
                self._user_repo,
                user,
                auth_result,
                session=self._db,
                community_id=self._community_id,
                provider_id=provider.id,
            )

    async def provision_user(
        self,
        auth_result: OAuthAuthResult,
        provider: OAuthProvider,
        role: str,
    ) -> User:
        """
        @brief Gate, provision and sync the user (profile, role, subgroups).

        @param auth_result Extracted claims from token.
        @param provider OAuth provider configuration.
        @param role Resolved community role.
        @return The user (created or updated).
        @raises SsoRefusedError sso_domain_not_allowed / sso_group_required /
                sso_no_account / sso_account_disabled / sso_email_unverified /
                sso_email_unverified_local / sso_email_taken.
        """
        link = await self._link_repo.find_by_provider_and_sub(provider.id, auth_result.sub)
        linked = await self._user_repo.get_by_id(link.user_id) if link else None
        email_user = None
        if link is None and auth_result.email and auth_result.email_verified:
            email_user = await self._user_repo.find_by_email(auth_result.email.strip().lower())
        decision = evaluate_gates(provider, auth_result, link, linked, email_user)
        if decision.code:
            # A refused linked user is signed out everywhere.
            raise await self._refuse(decision.code, link.user_id if link else None)
        if linked is not None and link is not None:
            await self._sync_returning(linked, link, auth_result, provider, role)
            user = linked
        elif email_user is not None:
            user = await self._link_existing(email_user, auth_result, provider, role)
        else:
            email = (auth_result.email or "").strip().lower()
            user = await self._create_user(email, auth_result, provider, role)
        if not has_subgroup_rules(provider.claim_mapping):
            return user
        if self.pending_link is not None:
            mapped = await resolve_subgroup_mappings(
                SubgroupRepository(self._db),
                self._community_id,
                auth_result.groups or [],
                provider.claim_mapping,
            )
            # Applied by pending_link.create_link once the second factor passes.
            self.pending_link["subgroups"] = {str(k): v for k, v in mapped.items()}
            return user
        await apply_subgroup_mappings(
            SubgroupRepository(self._db),
            SubgroupMemberRepository(self._db),
            self._community_id,
            user.id,
            auth_result.groups or [],
            provider.claim_mapping,
            session=self._db,
            provider_id=provider.id,
        )
        return user

    @staticmethod
    def _maps_roles(provider: OAuthProvider) -> bool:
        """@brief Role sync only when the provider actively maps groups to roles."""
        return bool(provider.group_mappings) or bool(global_role_mappings(provider.claim_mapping))

    async def _sync_role(self, user: User, role: str, provider: OAuthProvider) -> None:
        """@brief Apply a group-mapped role change and audit it (never demotes the last admin)."""
        if not self._maps_roles(provider) or user.role == role:
            return
        old = user.role
        if not await can_change_role(self._user_repo, self._community_id, user, role):
            await audit_role_sync_skipped(self._db, user.id, old, role, provider.id)
            return
        await self._user_repo.update(user, {"role": role})
        await audit_role_synced(self._db, user.id, old, role, provider_id=provider.id)

    async def _sync_returning(
        self,
        user: User,
        link: UserOAuthLink,
        auth_result: OAuthAuthResult,
        provider: OAuthProvider,
        role: str,
    ) -> None:
        """@brief Login over an existing link: role, profile and link-data sync."""
        await self._sync_role(user, role, provider)
        await self._sync_profile(user, auth_result, provider)
        link_updates: dict[str, object] = {}
        if auth_result.email and auth_result.email != link.email_from_provider:
            link_updates["email_from_provider"] = auth_result.email
        if auth_result.avatar_url and auth_result.avatar_url != link.avatar_url:
            link_updates["avatar_url"] = auth_result.avatar_url
        if link_updates:
            await self._link_repo.update(link, link_updates)

    async def _link_existing(
        self,
        user: User,
        auth_result: OAuthAuthResult,
        provider: OAuthProvider,
        role: str,
    ) -> User:
        """
        @brief First SSO login for an existing account (gates already passed): link it.

        A first link to an account with a local factor is held (pending_link)
        until that factor passes; nothing is written here in that case.
        """
        if await factor_methods(self._db, user):
            self.pending_link = {
                "provider_id": str(provider.id),
                "sub": auth_result.sub,
                "email_from_provider": auth_result.email,
                "avatar_url": auth_result.avatar_url,
                "role": role if self._maps_roles(provider) and user.role != role else None,
            }
            return user
        await self._sync_role(user, role, provider)
        await self._sync_profile(user, auth_result, provider)
        await self._create_link(user, provider, auth_result)
        return user

    async def _create_link(
        self, user: User, provider: OAuthProvider, auth_result: OAuthAuthResult
    ) -> None:
        """@brief Persist the (provider, sub) link for ``user``."""
        await self._link_repo.create(
            UserOAuthLink(
                user_id=user.id,
                provider_id=provider.id,
                sub=auth_result.sub,
                email_from_provider=auth_result.email,
                avatar_url=auth_result.avatar_url,
            )
        )

    async def _create_user(
        self,
        email: str,
        auth_result: OAuthAuthResult,
        provider: OAuthProvider,
        role: str,
    ) -> User:
        """@brief JIT-create a user (username from username_claim, deduped -2, -3...).

        @raises SsoRefusedError sso_email_taken when the email belongs to another
                (e.g. soft-deleted) account; no insert is attempted.
        """
        if await self._user_repo.email_owner_id(email) is not None:
            raise SsoRefusedError("sso_email_taken")
        base = clean_username(auth_result.username) or _derive_username(
            auth_result.display_name, auth_result.email
        )
        lost: set[str] = set()
        created: User | None = None
        for _attempt in range(CREATE_ATTEMPTS):
            username = await unique_username(self._user_repo, base, exclude=lost)
            created = await self._user_repo.try_create(
                User(
                    community_id=self._community_id,
                    email=email,
                    username=username,
                    display_name=auth_result.display_name or username,
                    role=role,
                    email_verified=True,
                    avatar_url=auth_result.avatar_url,
                )
            )
            if created is not None:
                break
            lost.add(username)  # lost a concurrent race for this name
        if created is None:
            raise AppError(
                code="sso_provision_conflict",
                message="Could not create account, try again",
                status_code=409,
            )
        user = created
        await self._create_link(user, provider, auth_result)
        await CalendarRepository(self._db).ensure_personal(self._community_id, user.id)
        return user
