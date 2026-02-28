"""
@file user_repo.py
@brief User repository with identity and profile query methods.

Extends :class:`BaseRepository` with auth-specific lookups (by email,
username, OIDC subject) and profile-related operations.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """
    @brief Async repository for :class:`User` entities.

    All queries filter out soft-deleted rows by default (via ``_base_query``).
    """

    model = User

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def find_by_email(self, email: str) -> User | None:
        """
        @brief Look up a user by email address (case-insensitive).

        @param email Email to search for.
        @return The matching User or None.
        """
        from sqlalchemy import func as sa_func

        stmt = self._base_query().where(sa_func.lower(User.email) == email.lower())
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_username(self, username: str) -> User | None:
        """
        @brief Look up a user by username (case-insensitive).

        @param username Username to search for.
        @return The matching User or None.
        """
        from sqlalchemy import func as sa_func

        stmt = self._base_query().where(sa_func.lower(User.username) == username.lower())
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_oidc_sub(self, oidc_sub: str) -> User | None:
        """
        @brief Look up a user by OIDC subject identifier.

        @param oidc_sub The ``sub`` claim from the OIDC id_token.
        @return The matching User or None.
        """
        stmt = self._base_query().where(User.oidc_sub == oidc_sub)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_last_seen(self, user_id: uuid.UUID) -> None:
        """
        @brief Touch the user's ``last_seen_at`` timestamp.

        @param user_id UUID of the user to update.
        """
        stmt = update(User).where(User.id == user_id).values(last_seen_at=datetime.now(UTC))
        await self._session.execute(stmt)

    async def update_totp(
        self,
        user_id: uuid.UUID,
        *,
        totp_secret: str | None = None,
        totp_enabled: bool | None = None,
    ) -> None:
        """
        @brief Update TOTP-related fields on a user.

        @param user_id UUID of the user.
        @param totp_secret New TOTP secret (or None to clear).
        @param totp_enabled Whether TOTP is active.
        """
        values: dict[str, Any] = {}
        if totp_secret is not None:
            values["totp_secret"] = totp_secret
        if totp_enabled is not None:
            values["totp_enabled"] = totp_enabled
        if values:
            stmt = update(User).where(User.id == user_id).values(**values)
            await self._session.execute(stmt)

    async def email_exists(self, email: str) -> bool:
        """
        @brief Check whether an email is already registered.

        @param email Email to check.
        @return True if a non-deleted user with this email exists.
        """
        user = await self.find_by_email(email)
        return user is not None

    async def username_exists(self, username: str) -> bool:
        """
        @brief Check whether a username is already taken.

        @param username Username to check.
        @return True if a non-deleted user with this username exists.
        """
        user = await self.find_by_username(username)
        return user is not None

    async def list_by_community(
        self,
        community_id: uuid.UUID,
        *,
        limit: int = 20,
        cursor: str | None = None,
    ) -> tuple[list[User], str | None]:
        """
        @brief List users belonging to a community with cursor pagination.

        @param community_id Community scope.
        @param limit Max items to return.
        @param cursor Opaque cursor from previous page.
        @return Tuple of (users, next_cursor).
        """
        return await self.list(community_id, limit=limit, cursor=cursor)

    async def list_by_community_search(
        self,
        community_id: uuid.UUID,
        *,
        search: str | None = None,
        limit: int = 20,
        cursor: str | None = None,
    ) -> tuple[list[User], str | None]:
        """
        @brief List users with optional search filter (username, display_name, email).

        @param community_id Community scope.
        @param search Optional search string (ILIKE on username, display_name, email).
        @param limit Max items to return.
        @param cursor Opaque cursor from previous page.
        @return Tuple of (users, next_cursor).
        """
        from sqlalchemy import or_

        stmt = self._base_query().where(User.community_id == community_id)
        if search and search.strip():
            term = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    User.username.ilike(term),
                    User.display_name.ilike(term),
                    User.email.ilike(term),
                ),
            )
        stmt = stmt.order_by(User.created_at.desc())
        if cursor:
            try:
                cursor_id = uuid.UUID(cursor)
                stmt = stmt.where(User.id < cursor_id)
            except ValueError:
                pass
        stmt = stmt.limit(limit + 1)
        result = await self._session.execute(stmt)
        rows = list(result.scalars().all())
        next_cursor: str | None = None
        if len(rows) > limit:
            rows = rows[:limit]
            next_cursor = str(rows[-1].id)
        return rows, next_cursor

    async def get_by_id_include_deleted(
        self, user_id: uuid.UUID, community_id: uuid.UUID | None = None
    ) -> User | None:
        """
        @brief Fetch a user by ID including soft-deleted users.

        Used by admin restore operations.

        @param user_id UUID of the user.
        @param community_id Optional community scope.
        @return The User or None.
        """
        stmt = select(User).where(User.id == user_id)
        if community_id is not None:
            stmt = stmt.where(User.community_id == community_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
