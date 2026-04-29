"""
@file test_subgroup_media_service.py
@brief Unit tests for subgroup media service.

Tests authorization checks and source filter pass-through.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import AuthorizationError
from app.models.subgroup import Subgroup
from app.models.user import User
from app.repositories.subgroup_media_repo import SubgroupMediaRepository
from app.repositories.subgroup_repo import SubgroupRepository
from app.services.subgroups.subgroup_media_service import SubgroupMediaService

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _make_user(user_id: uuid.UUID | None = None) -> MagicMock:
    """@brief Build a mock User."""
    user = MagicMock(spec=User)
    user.id = user_id or uuid.uuid4()
    user.role = "member"
    return user


def _make_subgroup(
    sg_id: uuid.UUID | None = None,
    is_private: bool = False,
) -> MagicMock:
    """@brief Build a mock Subgroup."""
    sg = MagicMock(spec=Subgroup)
    sg.id = sg_id or uuid.uuid4()
    sg.community_id = COMMUNITY_ID
    sg.name = "Family"
    sg.is_private = is_private
    sg.created_at = datetime.now(UTC)
    return sg


@pytest.fixture
def subgroup_repo() -> AsyncMock:
    repo = AsyncMock(spec=SubgroupRepository)
    repo.is_member = AsyncMock()
    repo.get_by_id = AsyncMock()
    return repo


@pytest.fixture
def media_repo() -> AsyncMock:
    return AsyncMock(spec=SubgroupMediaRepository)


@pytest.fixture
def service(subgroup_repo, media_repo) -> SubgroupMediaService:
    return SubgroupMediaService(
        subgroup_repo=subgroup_repo,
        media_repo=media_repo,
        community_id=COMMUNITY_ID,
    )


class TestListMedia:
    """@brief Tests for list_media method."""

    async def test_rejects_unauthenticated_user(self, service, subgroup_repo):
        """@brief Rejects request from non-member."""
        user = _make_user()
        sg = _make_subgroup(is_private=True)
        subgroup_repo.get_by_id.return_value = sg
        subgroup_repo.is_member.return_value = False

        with pytest.raises(AuthorizationError):
            await service.list_media(
                subgroup_id=sg.id,
                viewer_id=user.id,
                source="all",
                cursor=None,
                limit=60,
            )

    async def test_accepts_public_subgroup_member(self, service, subgroup_repo, media_repo):
        """@brief Accepts request from member of public subgroup."""
        user = _make_user()
        sg = _make_subgroup(is_private=False)
        subgroup_repo.get_by_id.return_value = sg
        media_repo.list_media.return_value = ([], None)

        items, cursor = await service.list_media(
            subgroup_id=sg.id,
            viewer_id=user.id,
            source="all",
            cursor=None,
            limit=60,
        )

        assert items == []
        assert cursor is None
        media_repo.list_media.assert_called_once()

    async def test_passes_source_filter(self, service, subgroup_repo, media_repo):
        """@brief Passes source filter to repo."""
        user = _make_user()
        sg = _make_subgroup()
        subgroup_repo.get_by_id.return_value = sg
        media_repo.list_media.return_value = ([], None)

        await service.list_media(
            subgroup_id=sg.id,
            viewer_id=user.id,
            source="gallery",
            cursor=None,
            limit=60,
        )

        call_kwargs = media_repo.list_media.call_args[1]
        assert call_kwargs["source"] == "gallery"

    async def test_passes_pagination(self, service, subgroup_repo, media_repo):
        """@brief Passes cursor and limit to repo."""
        user = _make_user()
        sg = _make_subgroup()
        subgroup_repo.get_by_id.return_value = sg
        media_repo.list_media.return_value = ([], None)

        await service.list_media(
            subgroup_id=sg.id,
            viewer_id=user.id,
            source="all",
            cursor="2025-04-28T10:00:00+00:00:550e8400-e29b-41d4-a716-446655440000",
            limit=120,
        )

        call_kwargs = media_repo.list_media.call_args[1]
        cursor_val = "2025-04-28T10:00:00+00:00:550e8400-e29b-41d4-a716-446655440000"
        assert call_kwargs["cursor"] == cursor_val
        assert call_kwargs["limit"] == 120
