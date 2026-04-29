"""
@file test_gallery_repo.py
@brief Unit tests for GalleryRepository.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.gallery import Gallery
from app.repositories.gallery_repo import GalleryRepository

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
OWNER_ID, GALLERY_ID, VIEWER_ID = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()


def _make_session() -> AsyncMock:
    """@brief Create a mock AsyncSession with common stubs."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    return session


class TestGalleryRepositoryListVisible:
    """@brief Tests for GalleryRepository.list_visible()."""

    @pytest.mark.asyncio
    async def test_filters_by_subgroup_id(self):
        """list_visible should filter galleries by subgroup_id when provided."""
        session = _make_session()
        subgroup_id = uuid.uuid4()
        now = datetime.now(UTC)

        gallery = MagicMock(spec=Gallery)
        gallery.id = GALLERY_ID
        gallery.owner_id = OWNER_ID
        gallery.title = "Group Gallery"
        gallery.visibility = "subgroup"
        gallery.subgroup_id = subgroup_id
        gallery.created_at = gallery.updated_at = now
        gallery.item_count = 5

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [gallery]
        session.execute = AsyncMock(return_value=mock_result)

        repo = GalleryRepository(session)
        result, next_cursor = await repo.list_visible(
            COMMUNITY_ID,
            viewer_id=VIEWER_ID,
            subgroup_ids=[subgroup_id],
            subgroup_id=subgroup_id,
            limit=20,
        )

        assert len(result) == 1
        assert result[0].id == GALLERY_ID
        assert result[0].subgroup_id == subgroup_id
        session.execute.assert_awaited_once()
