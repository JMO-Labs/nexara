"""
@file interest_service.py
@brief Service for managing user interest profiles.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

import structlog

from app.core.exceptions import ConflictError, NotFoundError
from app.models.interest import UserInterest
from app.repositories.interest_repo import InterestCategoryRepository, InterestRepository
from app.schemas.interest import (
    InterestAnalytics,
    InterestCategoryResponse,
    InterestResponse,
    UserInterestsResponse,
)

logger = structlog.get_logger(__name__)


class InterestService:
    """@brief Service for interest profile operations."""

    def __init__(
        self,
        interest_repo: InterestRepository,
        category_repo: InterestCategoryRepository,
        community_id: uuid.UUID,
    ) -> None:
        self._interest_repo = interest_repo
        self._category_repo = category_repo
        self._community_id = community_id

    async def add_interest(
        self,
        user_id: uuid.UUID,
        category_slug: str,
        value: str,
        source: str = "manual",
    ) -> UserInterest:
        """
        @brief Add an interest for a user.

        @param user_id User ID.
        @param category_slug Category slug.
        @param value Interest value.
        @param source Source of the interest (default: manual).
        @return The created UserInterest.
        @raises NotFoundError If category does not exist.
        @raises ConflictError If duplicate interest exists.
        """
        category = await self._category_repo.get_by_slug(category_slug)
        if category is None:
            raise NotFoundError(message="Interest category not found")

        existing = await self._interest_repo.find_duplicate(user_id, category_slug, value)
        if existing is not None:
            raise ConflictError(message="Interest already exists")

        interest = UserInterest(
            user_id=user_id,
            category_slug=category_slug,
            value=value,
            source=source,
            confidence=Decimal("1.00"),
        )
        return await self._interest_repo.create(interest)

    async def remove_interest(
        self,
        interest_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """
        @brief Remove an interest for a user.

        @param interest_id Interest ID.
        @param user_id User ID (must own the interest).
        @raises NotFoundError If interest not found or not owned.
        """
        deleted = await self._interest_repo.delete_by_id(interest_id, user_id)
        if not deleted:
            raise NotFoundError(message="Interest not found")

    async def list_user_interests(self, user_id: uuid.UUID) -> UserInterestsResponse:
        """
        @brief List all interests and categories for a user.

        @param user_id User ID.
        @return UserInterestsResponse with interests and categories.
        """
        interests = await self._interest_repo.list_for_user(user_id)
        categories = await self._category_repo.list_all()

        return UserInterestsResponse(
            interests=[InterestResponse.model_validate(i) for i in interests],
            categories=[InterestCategoryResponse.model_validate(c) for c in categories],
        )

    async def get_analytics(self) -> list[InterestAnalytics]:
        """
        @brief Get aggregated interest counts for the community.

        @return List of InterestAnalytics.
        """
        rows = await self._interest_repo.analytics(
            self._community_id,
            limit=50,
        )
        return [
            InterestAnalytics(
                category_slug=cat,
                value=val,
                count=cnt,
            )
            for cat, val, cnt in rows
        ]

    async def list_categories(self) -> list[InterestCategoryResponse]:
        """
        @brief List all interest categories.

        @return List of InterestCategoryResponse.
        """
        categories = await self._category_repo.list_all()
        return [InterestCategoryResponse.model_validate(c) for c in categories]

    async def suggest_for_user(
        self,
        user_id: uuid.UUID,
        category_slug: str,
        source_text: str,
    ) -> None:
        """
        @brief Record an interest suggestion from a prompt reply (non-blocking).

        Logs the suggestion event only. This is a suggestion, not an auto-add to
        the user's interests. Intentionally not persisted: nothing consumes
        suggestions (no dismissal or admin review flow), so a table would be
        unused state. Revisit if such a flow is added.

        @param user_id User ID.
        @param category_slug Interest category slug.
        @param source_text The text that triggered the suggestion (e.g., prompt reply).
        """
        logger.info(
            "interest.suggested",
            user_id=str(user_id),
            category_slug=category_slug,
            source_text=source_text,
        )
