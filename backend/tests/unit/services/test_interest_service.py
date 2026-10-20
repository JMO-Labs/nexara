"""
@file test_interest_service.py
@brief Unit tests for InterestService.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import ConflictError, NotFoundError
from app.models.interest import InterestCategory, UserInterest
from app.repositories.interest_repo import InterestCategoryRepository, InterestRepository
from app.services.interest_service import InterestService

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
USER_ID = uuid.uuid4()


def _make_user_interest(**overrides) -> MagicMock:
    """@brief Build a mock UserInterest with sensible defaults."""
    interest = MagicMock(spec=UserInterest)
    interest.id = overrides.get("id", uuid.uuid4())
    interest.user_id = overrides.get("user_id", USER_ID)
    interest.category_slug = overrides.get("category_slug", "hobbies")
    interest.value = overrides.get("value", "hiking")
    interest.source = overrides.get("source", "manual")
    interest.confidence = overrides.get("confidence", Decimal("1.00"))
    interest.created_at = overrides.get("created_at", datetime.now(UTC))
    return interest


def _make_interest_category(**overrides) -> MagicMock:
    """@brief Build a mock InterestCategory with sensible defaults."""
    category = MagicMock(spec=InterestCategory)
    category.slug = overrides.get("slug", "hobbies")
    category.label = overrides.get("label", "Hobbies")
    category.description = overrides.get("description", "Activities")
    category.icon = overrides.get("icon", "puzzle-piece")
    category.multi_value = overrides.get("multi_value", True)
    category.sort_order = overrides.get("sort_order", 10)
    return category


@pytest.fixture
def interest_repo():
    return AsyncMock(spec=InterestRepository)


@pytest.fixture
def category_repo():
    return AsyncMock(spec=InterestCategoryRepository)


@pytest.fixture
def service(interest_repo, category_repo):
    return InterestService(
        interest_repo=interest_repo,
        category_repo=category_repo,
        community_id=COMMUNITY_ID,
    )


class TestAddInterest:
    @pytest.mark.asyncio
    async def test_add_interest_creates_record(self, service, interest_repo, category_repo):
        category = MagicMock(spec=InterestCategory)
        category.slug = "hobbies"
        category_repo.get_by_slug.return_value = category
        interest_repo.find_duplicate.return_value = None
        new_interest = MagicMock(spec=UserInterest)
        interest_repo.create.return_value = new_interest

        result = await service.add_interest(USER_ID, "hobbies", "hiking")

        assert result is new_interest
        interest_repo.create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_add_duplicate_interest_rejected(self, service, interest_repo, category_repo):
        category = MagicMock(spec=InterestCategory)
        category_repo.get_by_slug.return_value = category
        existing = MagicMock(spec=UserInterest)
        interest_repo.find_duplicate.return_value = existing

        with pytest.raises(ConflictError):
            await service.add_interest(USER_ID, "hobbies", "hiking")

    @pytest.mark.asyncio
    async def test_add_interest_invalid_category_raises(self, service, category_repo):
        category_repo.get_by_slug.return_value = None

        with pytest.raises(NotFoundError):
            await service.add_interest(USER_ID, "nonexistent", "value")


class TestRemoveInterest:
    @pytest.mark.asyncio
    async def test_remove_interest_deletes_record(self, service, interest_repo):
        interest_repo.delete_by_id.return_value = True

        await service.remove_interest(uuid.uuid4(), USER_ID)

        interest_repo.delete_by_id.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_remove_nonexistent_raises(self, service, interest_repo):
        interest_repo.delete_by_id.return_value = False

        with pytest.raises(NotFoundError):
            await service.remove_interest(uuid.uuid4(), USER_ID)


class TestListUserInterests:
    @pytest.mark.asyncio
    async def test_list_user_interests_returns_grouped(self, service, interest_repo, category_repo):
        interests = [_make_user_interest()]
        interest_repo.list_for_user.return_value = interests
        categories = [_make_interest_category()]
        category_repo.list_all.return_value = categories

        result = await service.list_user_interests(USER_ID)

        assert len(result.interests) == 1
        assert len(result.categories) == 1


class TestAnalytics:
    @pytest.mark.asyncio
    async def test_interest_analytics_returns_counts(self, service, interest_repo):
        interest_repo.analytics.return_value = [
            ("hobbies", "hiking", 5),
            ("music", "guitar", 3),
        ]

        result = await service.get_analytics()

        assert len(result) == 2
        assert result[0].category_slug == "hobbies"
        assert result[0].count == 5
