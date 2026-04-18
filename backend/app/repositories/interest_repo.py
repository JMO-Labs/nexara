"""
@file interest_repo.py
@brief Repositories for InterestCategory and UserInterest.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select

from app.models.interest import InterestCategory, UserInterest
from app.models.user import User
from app.repositories.base import BaseRepository


class InterestCategoryRepository(BaseRepository[InterestCategory]):
    """@brief Repository for interest categories."""

    model = InterestCategory

    async def get_by_slug(self, slug: str) -> InterestCategory | None:
        """
        @brief Fetch a category by slug (primary key).

        @param slug Category slug.
        @return The category or None.
        """
        stmt = self._base_query().where(InterestCategory.slug == slug)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(self) -> list[InterestCategory]:
        """
        @brief List all categories ordered by sort_order.

        @return List of categories.
        """
        stmt = self._base_query().order_by(
            InterestCategory.sort_order.asc(), InterestCategory.slug.asc()
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())


class InterestRepository(BaseRepository[UserInterest]):
    """@brief Repository for user interests."""

    model = UserInterest

    async def find_duplicate(
        self,
        user_id: uuid.UUID,
        category_slug: str,
        value: str,
    ) -> UserInterest | None:
        """
        @brief Find an existing interest for the same user/category/value.

        @param user_id User ID.
        @param category_slug Category slug.
        @param value Interest value.
        @return The existing interest or None.
        """
        stmt = self._base_query().where(
            UserInterest.user_id == user_id,
            UserInterest.category_slug == category_slug,
            UserInterest.value == value,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: uuid.UUID) -> list[UserInterest]:
        """
        @brief List all interests for a user.

        @param user_id User ID.
        @return List of user interests.
        """
        stmt = (
            self._base_query()
            .where(UserInterest.user_id == user_id)
            .order_by(
                UserInterest.category_slug.asc(),
                UserInterest.value.asc(),
            )
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def analytics(
        self,
        community_id: uuid.UUID,
        limit: int = 50,
    ) -> list[tuple[str, str, int]]:
        """
        @brief Aggregate interest counts by category and value, scoped to community.

        @param community_id Community ID (users must belong to this community).
        @param limit Max number of results.
        @return List of (category_slug, value, count) tuples.
        """
        stmt = (
            select(
                UserInterest.category_slug,
                UserInterest.value,
                func.count(UserInterest.id).label("count"),
            )
            .join(User, UserInterest.user_id == User.id)
            .where(
                User.community_id == community_id,
                User.deleted_at.is_(None),
            )
            .group_by(UserInterest.category_slug, UserInterest.value)
            .order_by(func.count(UserInterest.id).desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [(row[0], row[1], row[2]) for row in result.all()]

    async def delete_by_id(
        self,
        interest_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """
        @brief Delete an interest by ID, ensuring the user owns it.

        @param interest_id Interest ID.
        @param user_id User ID (must own the interest).
        @return True if deleted, False if not found or not owned.
        """
        stmt = select(UserInterest).where(
            UserInterest.id == interest_id,
            UserInterest.user_id == user_id,
        )
        result = await self._session.execute(stmt)
        interest = result.scalar_one_or_none()
        if interest is None:
            return False
        await self._session.delete(interest)
        await self._session.flush()
        return True
