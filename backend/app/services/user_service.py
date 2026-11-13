"""
@file user_service.py
@brief User profile and account management business logic.

Handles profile reading/updating, Gravatar URL generation,
password changes, and account deletion.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import AuthenticationError, ConflictError, NotFoundError
from app.core.i18n import _
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.repositories.moderation_repo import ModerationRepository
from app.repositories.token_repo import TokenRepository
from app.repositories.user_repo import UserRepository

logger = structlog.get_logger(__name__)

GRAVATAR_BASE = "https://www.gravatar.com/avatar"


class UserService:
    """
    @brief Stateless service for user profile and account operations.

    @param session Async DB session.
    @param settings App settings.
    """

    def __init__(
        self,
        session: AsyncSession,
        settings: Settings | None = None,
    ) -> None:
        self._session = session
        self._settings = settings or get_settings()
        self._user_repo = UserRepository(session)
        self._token_repo = TokenRepository(session)
        self._moderation_repo = ModerationRepository(session)

    async def list_blocked(self, viewer: User) -> list[User]:
        """
        @brief List users the viewer has blocked.

        @param viewer Authenticated user.
        @return Blocked User rows.
        """
        return await self._moderation_repo.list_blocked_users(viewer.id, viewer.community_id)

    async def get_user(self, user_id: uuid.UUID) -> User:
        """
        @brief Fetch a single user by ID.

        @param user_id UUID of the user to fetch.
        @return The User model instance.
        @raises NotFoundError If the user does not exist.
        """
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError(message=_("User not found"))
        return user

    async def get_user_by_username(self, username: str) -> User:
        """
        @brief Fetch a user by username.

        @param username The username to look up.
        @return The User model instance.
        @raises NotFoundError If the user does not exist.
        """
        user = await self._user_repo.find_by_username(username)
        if not user:
            raise NotFoundError(message=_("User not found"))
        return user

    async def list_users(
        self,
        community_id: uuid.UUID,
        *,
        limit: int = 20,
        cursor: str | None = None,
    ) -> tuple[list[User], str | None]:
        """
        @brief List users in a community with cursor pagination.

        @param community_id Community scope.
        @param limit Max items per page.
        @param cursor Opaque cursor from previous response.
        @return Tuple of (users, next_cursor).
        """
        return await self._user_repo.list_by_community(
            community_id,
            limit=limit,
            cursor=cursor,
        )

    async def update_profile(self, user: User, data: dict[str, Any]) -> User:
        """
        @brief Update profile fields on the authenticated user.

        @param user The current user.
        @param data Dict of field names to new values.
        @return The updated User.
        """
        allowed = {
            "display_name",
            "bio",
            "title",
            "location",
            "website_url",
            "birthday",
            "pronouns",
        }
        filtered = {k: v for k, v in data.items() if k in allowed and v is not None}
        if not filtered:
            return user

        updated = await self._user_repo.update(user, filtered)
        logger.info("profile_updated", user_id=str(user.id), fields=list(filtered.keys()))
        return updated

    async def change_password(
        self,
        user: User,
        current_password: str,
        new_password: str,
    ) -> None:
        """
        @brief Change the user's password and revoke all refresh tokens.

        @param user The current user.
        @param current_password Existing password for verification.
        @param new_password The new password.
        @raises AuthenticationError If the current password is wrong.
        """
        if not user.password_hash:
            raise AuthenticationError(message=_("Account uses external authentication"))

        if not verify_password(current_password, user.password_hash):
            raise AuthenticationError(message=_("Current password is incorrect"))

        await self._user_repo.update(user, {"password_hash": hash_password(new_password)})
        await self._token_repo.revoke_all_for_user(user.id)
        logger.info("password_changed", user_id=str(user.id))

    async def change_email(
        self,
        user: User,
        new_email: str,
        password: str,
    ) -> User:
        """
        @brief Change the user's email after password verification.

        @param user The current user.
        @param new_email The new email address.
        @param password Current password for verification.
        @return The updated User.
        @raises AuthenticationError If the password is wrong.
        @raises ConflictError If the new email is already taken.
        """
        if not user.password_hash or not verify_password(password, user.password_hash):
            raise AuthenticationError(message=_("Invalid password"))

        if await self._user_repo.email_exists(new_email):
            raise ConflictError(message=_("Email is already registered"))

        updated = await self._user_repo.update(
            user,
            {"email": new_email, "email_verified": False},
        )
        logger.info("email_changed", user_id=str(user.id))
        return updated

    async def deactivate_account(self, user: User) -> None:
        """
        @brief Soft-delete the user's account and revoke all tokens.

        @param user The user to deactivate.
        """
        await self._user_repo.soft_delete(user)
        await self._token_repo.revoke_all_for_user(user.id)
        logger.info("account_deactivated", user_id=str(user.id))

    async def complete_onboarding(self, user: User) -> User:
        """
        @brief Mark the onboarding tour as completed for the user.

        @param user The current user.
        @return The updated User.
        """
        updated = await self._user_repo.update(
            user,
            {"tour_completed_at": datetime.now(UTC)},
        )
        logger.info("onboarding_completed", user_id=str(user.id))
        return updated

    @staticmethod
    def get_avatar_url(user: User, size: int = 80) -> str:
        """
        @brief Return the user's avatar URL, falling back to Gravatar.

        Gravatar uses an MD5 hash of the lowercase email.  The ``d=mp``
        parameter returns a generic silhouette for emails without a Gravatar.

        @param user The User model instance.
        @param size Avatar size in pixels.
        @return URL string.
        """
        if user.avatar_url:
            return user.avatar_url
        email_hash = hashlib.md5(user.email.strip().lower().encode()).hexdigest()  # noqa: S324
        return f"{GRAVATAR_BASE}/{email_hash}?s={size}&d=mp"
