"""
@file test_home_service_aggregated.py
@brief Unit tests for HomeService community-level scope aggregators (Phase 4).

Tests for list_media with scope='all', 'community', 'subgroup' and the
union-based list_aggregated repository methods.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.subgroup import Subgroup
from app.models.user import User
from app.repositories.event_repo import EventRepository
from app.repositories.notification_repo import NotificationRepository
from app.repositories.post_repo import PostRepository
from app.repositories.subgroup_media_repo import SubgroupMediaRepository
from app.repositories.subgroup_repo import SubgroupRepository

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
USER_ID = uuid.uuid4()
NOW = datetime(2026, 4, 29, 12, 0, 0, tzinfo=UTC)


def _make_user() -> MagicMock:
    """@brief Build a mock User for tests."""
    user = MagicMock(spec=User)
    user.id = USER_ID
    user.community_id = COMMUNITY_ID
    return user


def _build_service(
    post_repo: AsyncMock | None = None,
    event_repo: AsyncMock | None = None,
    notification_repo: AsyncMock | None = None,
    subgroup_repo: AsyncMock | None = None,
    media_repo: AsyncMock | None = None,
):
    """@brief Construct HomeService with mocked repos."""
    from app.services.home_service import HomeService

    return HomeService(
        post_repo=post_repo or AsyncMock(spec=PostRepository),
        event_repo=event_repo or AsyncMock(spec=EventRepository),
        notification_repo=notification_repo or AsyncMock(spec=NotificationRepository),
        subgroup_repo=subgroup_repo or AsyncMock(spec=SubgroupRepository),
        media_repo=media_repo or AsyncMock(spec=SubgroupMediaRepository),
        community_id=COMMUNITY_ID,
    )


class TestListMediaAggregated:
    """@brief Tests for HomeService.list_media() with community-level scoping."""

    @pytest.mark.asyncio
    async def test_list_media_scope_all_returns_union(self):
        """list_media(scope='all') returns community-root + subgroups."""
        user = _make_user()

        item_a = {
            "media_id": str(uuid.uuid4()),
            "source": "post",
            "created_at": "2026-04-28T10:00:00",
        }

        subgroup_repo = AsyncMock(spec=SubgroupRepository)
        subgroup_repo.list_visible_for_user.return_value = []

        media_repo = AsyncMock(spec=SubgroupMediaRepository)
        media_repo.list_aggregated.return_value = ([item_a], None)

        svc = _build_service(subgroup_repo=subgroup_repo, media_repo=media_repo)
        items, next_cursor = await svc.list_media(user=user, limit=24, scope="all")

        assert len(items) == 1
        media_repo.list_aggregated.assert_awaited_once()
        call_kwargs = media_repo.list_aggregated.call_args.kwargs
        assert call_kwargs["scope"] == "all"
        assert call_kwargs["community_id"] == COMMUNITY_ID
        assert call_kwargs["viewer_id"] == USER_ID

    @pytest.mark.asyncio
    async def test_list_media_scope_community_returns_only_root(self):
        """list_media(scope='community') returns only community-root (subgroup_id IS NULL)."""
        user = _make_user()

        item_community = {
            "media_id": str(uuid.uuid4()),
            "source": "post",
            "created_at": "2026-04-28T10:00:00",
        }

        subgroup_repo = AsyncMock(spec=SubgroupRepository)
        subgroup_repo.list_visible_for_user.return_value = []

        media_repo = AsyncMock(spec=SubgroupMediaRepository)
        media_repo.list_aggregated.return_value = ([item_community], None)

        svc = _build_service(subgroup_repo=subgroup_repo, media_repo=media_repo)
        items, next_cursor = await svc.list_media(user=user, limit=24, scope="community")

        assert len(items) == 1
        media_repo.list_aggregated.assert_awaited_once()
        call_kwargs = media_repo.list_aggregated.call_args.kwargs
        assert call_kwargs["scope"] == "community"

    @pytest.mark.asyncio
    async def test_list_media_scope_subgroup_filters_by_id(self):
        """list_media(scope='subgroup') returns only items from that subgroup."""
        user = _make_user()
        target_sg_id = uuid.uuid4()

        item_sg = {
            "media_id": str(uuid.uuid4()),
            "source": "gallery",
            "created_at": "2026-04-27T10:00:00",
        }

        subgroup_repo = AsyncMock(spec=SubgroupRepository)
        subgroup_repo.list_visible_for_user.return_value = []

        media_repo = AsyncMock(spec=SubgroupMediaRepository)
        media_repo.list_aggregated.return_value = ([item_sg], None)

        svc = _build_service(subgroup_repo=subgroup_repo, media_repo=media_repo)
        items, next_cursor = await svc.list_media(
            user=user, limit=24, scope="subgroup", subgroup_id=target_sg_id
        )

        assert len(items) == 1
        call_kwargs = media_repo.list_aggregated.call_args.kwargs
        assert call_kwargs["scope"] == "subgroup"
        assert call_kwargs["subgroup_id"] == target_sg_id

    @pytest.mark.asyncio
    async def test_list_media_resolves_subgroup_ids_for_all_scope(self):
        """list_media(scope='all') resolves viewer's subgroup_ids and passes to aggregated."""
        user = _make_user()
        sg1 = uuid.uuid4()
        sg2 = uuid.uuid4()

        sg_obj_1 = MagicMock(spec=Subgroup)
        sg_obj_1.id = sg1
        sg_obj_2 = MagicMock(spec=Subgroup)
        sg_obj_2.id = sg2

        subgroup_repo = AsyncMock(spec=SubgroupRepository)
        subgroup_repo.list_visible_for_user.return_value = [sg_obj_1, sg_obj_2]

        media_repo = AsyncMock(spec=SubgroupMediaRepository)
        media_repo.list_aggregated.return_value = ([], None)

        svc = _build_service(subgroup_repo=subgroup_repo, media_repo=media_repo)
        await svc.list_media(user=user, limit=24, scope="all")

        call_kwargs = media_repo.list_aggregated.call_args.kwargs
        assert call_kwargs["subgroup_ids"] == [sg1, sg2]

    @pytest.mark.asyncio
    async def test_list_media_respects_limit(self):
        """list_media() respects the limit parameter."""
        user = _make_user()

        subgroup_repo = AsyncMock(spec=SubgroupRepository)
        subgroup_repo.list_visible_for_user.return_value = []

        media_repo = AsyncMock(spec=SubgroupMediaRepository)
        media_repo.list_aggregated.return_value = ([], None)

        svc = _build_service(subgroup_repo=subgroup_repo, media_repo=media_repo)
        await svc.list_media(user=user, limit=50, scope="all")

        call_kwargs = media_repo.list_aggregated.call_args.kwargs
        assert call_kwargs["limit"] == 50

    @pytest.mark.asyncio
    async def test_list_media_caps_limit_at_200(self):
        """list_media() caps limit at 200."""
        user = _make_user()

        subgroup_repo = AsyncMock(spec=SubgroupRepository)
        subgroup_repo.list_visible_for_user.return_value = []

        media_repo = AsyncMock(spec=SubgroupMediaRepository)
        media_repo.list_aggregated.return_value = ([], None)

        svc = _build_service(subgroup_repo=subgroup_repo, media_repo=media_repo)
        await svc.list_media(user=user, limit=500, scope="all")

        call_kwargs = media_repo.list_aggregated.call_args.kwargs
        assert call_kwargs["limit"] == 200
