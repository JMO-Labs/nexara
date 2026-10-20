"""
@file test_gallery_repo_aggregated.py
@brief Unit tests for GalleryRepository community-level scope aggregation (Phase 4).

Tests for list_aggregated with visibility union of community-root + subgroup galleries.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.gallery import Gallery
from app.repositories.gallery_repo import GalleryRepository

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
VIEWER_ID = uuid.uuid4()
OWNER_ID = uuid.uuid4()
SG_ID_1 = uuid.uuid4()
SG_ID_2 = uuid.uuid4()


def _make_session() -> AsyncMock:
    """@brief Create a mock AsyncSession with common stubs."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    return session


class TestGalleryRepositoryAggregated:
    """@brief Tests for GalleryRepository.list_aggregated() scope union (Phase 4)."""

    @pytest.mark.asyncio
    async def test_list_aggregated_scope_all_returns_community_and_subgroups(self):
        """list_aggregated(scope='all') returns community-root + subgroup galleries."""
        session = _make_session()

        # Mock community-root gallery
        gallery_community = MagicMock(spec=Gallery)
        gallery_community.id = uuid.uuid4()
        gallery_community.visibility = "community"
        gallery_community.subgroup_id = None
        gallery_community.created_at = datetime.now(UTC)

        # Mock subgroup gallery
        gallery_subgroup = MagicMock(spec=Gallery)
        gallery_subgroup.id = uuid.uuid4()
        gallery_subgroup.visibility = "subgroup"
        gallery_subgroup.subgroup_id = SG_ID_1
        gallery_subgroup.created_at = datetime.now(UTC)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [gallery_community, gallery_subgroup]
        session.execute = AsyncMock(return_value=mock_result)

        repo = GalleryRepository(session)
        galleries, next_cursor = await repo.list_aggregated(
            COMMUNITY_ID,
            viewer_id=VIEWER_ID,
            subgroup_ids=[SG_ID_1, SG_ID_2],
            scope="all",
            limit=20,
        )

        assert len(galleries) == 2

    @pytest.mark.asyncio
    async def test_list_aggregated_scope_community_returns_only_root(self):
        """list_aggregated(scope='community') returns only community-root galleries."""
        session = _make_session()

        # Mock community-root gallery only
        gallery_community = MagicMock(spec=Gallery)
        gallery_community.id = uuid.uuid4()
        gallery_community.visibility = "community"
        gallery_community.subgroup_id = None
        gallery_community.created_at = datetime.now(UTC)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [gallery_community]
        session.execute = AsyncMock(return_value=mock_result)

        repo = GalleryRepository(session)
        galleries, next_cursor = await repo.list_aggregated(
            COMMUNITY_ID,
            viewer_id=VIEWER_ID,
            subgroup_ids=[SG_ID_1, SG_ID_2],
            scope="community",
            limit=20,
        )

        assert len(galleries) == 1
        assert galleries[0].subgroup_id is None

    @pytest.mark.asyncio
    async def test_list_aggregated_scope_subgroup_returns_specific_subgroup_only(self):
        """list_aggregated(scope='subgroup') returns galleries from specific subgroup only."""
        session = _make_session()

        # Mock subgroup-specific gallery
        gallery_subgroup = MagicMock(spec=Gallery)
        gallery_subgroup.id = uuid.uuid4()
        gallery_subgroup.visibility = "subgroup"
        gallery_subgroup.subgroup_id = SG_ID_1
        gallery_subgroup.created_at = datetime.now(UTC)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [gallery_subgroup]
        session.execute = AsyncMock(return_value=mock_result)

        repo = GalleryRepository(session)
        galleries, next_cursor = await repo.list_aggregated(
            COMMUNITY_ID,
            viewer_id=VIEWER_ID,
            subgroup_ids=[SG_ID_1, SG_ID_2],
            scope="subgroup",
            subgroup_id=SG_ID_1,
            limit=20,
        )

        assert len(galleries) == 1
        assert galleries[0].subgroup_id == SG_ID_1

    @pytest.mark.asyncio
    async def test_list_aggregated_scope_subgroup_returns_empty_without_subgroup_id(self):
        """list_aggregated(scope='subgroup') returns empty when subgroup_id not provided."""
        session = _make_session()
        repo = GalleryRepository(session)
        galleries, next_cursor = await repo.list_aggregated(
            COMMUNITY_ID,
            viewer_id=VIEWER_ID,
            subgroup_ids=[SG_ID_1, SG_ID_2],
            scope="subgroup",
            subgroup_id=None,  # Missing required parameter
            limit=20,
        )

        assert galleries == []
        assert next_cursor is None
