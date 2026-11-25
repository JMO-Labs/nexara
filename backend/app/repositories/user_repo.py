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

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.household import HouseholdMember
from app.models.media import Media
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

    async def update_totp(self, user_id: uuid.UUID, **fields: Any) -> None:
        """
        @brief Update TOTP fields; passing ``None`` clears the column.

        @param user_id UUID of the user.
        @param fields Any of ``totp_secret``, ``totp_pending_secret``, ``totp_enabled``.
        """
        bad = set(fields) - {"totp_secret", "totp_pending_secret", "totp_enabled"}
        if bad:
            raise ValueError(f"unknown totp fields: {sorted(bad)}")
        if fields:
            await self._session.execute(update(User).where(User.id == user_id).values(**fields))

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
        @brief Check whether a username is already taken, by a user or by a
               household member's @handle (one mention namespace).

        @param username Username to check.
        @return True if a non-deleted user or live household handle has it.
        """
        if await self.find_by_username(username) is not None:
            return True
        stmt = select(HouseholdMember.id).where(
            HouseholdMember.handle == username.lower(), HouseholdMember.deleted_at.is_(None)
        )
        return (await self._session.execute(stmt.limit(1))).first() is not None

    async def try_create(self, user: User) -> User | None:
        """
        @brief Insert ``user`` inside a savepoint.

        @param user New (transient) user.
        @return The persisted user, or None on a unique violation (the outer
                transaction stays usable).
        """
        try:
            async with self._session.begin_nested():
                self._session.add(user)
                await self._session.flush()
        except IntegrityError:
            return None
        await self._session.refresh(user)
        return user

    async def email_owner_id(self, email: str) -> uuid.UUID | None:
        """
        @brief Id of the user holding ``email``, soft-deleted users included
               (the unique constraint spans them).

        @param email Email (case-insensitive).
        @return Owner id or None.
        """
        stmt = select(User.id).where(func.lower(User.email) == email.lower()).limit(1)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def count_active_admins(self, community_id: uuid.UUID) -> int:
        """
        @brief Number of active, non-deleted admins in a community.

        @param community_id Community scope.
        @return Admin count.
        """
        stmt = (
            select(func.count())
            .select_from(User)
            .where(User.community_id == community_id)
            .where(User.role == "admin")
            .where(User.is_active.is_(True))
            .where(User.deleted_at.is_(None))
        )
        return int((await self._session.execute(stmt)).scalar_one())

    async def admin_ids(self, community_id: uuid.UUID) -> list[uuid.UUID]:
        """@brief Ids of non-deleted admins in a community (alert recipients)."""
        stmt = select(User.id).where(
            User.community_id == community_id,
            User.role == "admin",
            User.deleted_at.is_(None),
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def display_names(self, ids: set[uuid.UUID]) -> dict[uuid.UUID, str]:
        """@brief ``{id: display_name}`` for the given user ids (deleted users included)."""
        if not ids:
            return {}
        res = await self._session.execute(
            select(User.id, User.display_name).where(User.id.in_(ids))
        )
        return {r.id: r.display_name for r in res}

    async def username_owner_id(self, username: str) -> uuid.UUID | None:
        """
        @brief Id of the user holding ``username``, soft-deleted users included.

        @param username Username (case-insensitive).
        @return Owner id or None.
        """
        stmt = select(User.id).where(func.lower(User.username) == username.lower()).limit(1)
        return (await self._session.execute(stmt)).scalar_one_or_none()

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

    async def get_many(
        self,
        user_ids: list[uuid.UUID] | set[uuid.UUID],
        community_id: uuid.UUID,
        *,
        viewer_id: uuid.UUID,
    ) -> list[User]:
        """
        @brief Batch-fetch live users of a community visible to ``viewer_id``.

        Users who blocked the viewer, or whom the viewer blocked, are excluded.

        @param user_ids Ids to fetch.
        @param community_id Tenant scope.
        @param viewer_id Requesting user (block filter).
        @return Matching users.
        """
        if not user_ids:
            return []
        from app.models.moderation import UserBlock

        blocked = select(UserBlock.blocked_id).where(UserBlock.blocker_id == viewer_id)
        blockers = select(UserBlock.blocker_id).where(UserBlock.blocked_id == viewer_id)
        stmt = self._base_query().where(
            User.id.in_(user_ids),
            User.community_id == community_id,
            User.id.notin_(blocked),
            User.id.notin_(blockers),
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def get_media(self, media_id: uuid.UUID) -> Media | None:
        """@brief Media row by id (used to vet a profile banner)."""
        return await self._session.get(Media, media_id)
