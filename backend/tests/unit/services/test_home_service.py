"""
@file test_home_service.py
@brief Unit tests for HomeService (summary + media aggregation).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.event import Event
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


def _make_user(last_seen_at: datetime | None = None) -> MagicMock:
    """@brief Build a mock User for tests."""
    user = MagicMock(spec=User)
    user.id = USER_ID
    user.community_id = COMMUNITY_ID
    user.last_seen_at = last_seen_at
    return user


def _make_subgroup(sg_id: uuid.UUID | None = None, name: str = "Alpha") -> MagicMock:
    """@brief Build a mock Subgroup."""
    sg = MagicMock(spec=Subgroup)
    sg.id = sg_id or uuid.uuid4()
    sg.name = name
    return sg


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


class TestSummary:
    """@brief Tests for HomeService.summary()."""

    @pytest.mark.asyncio
    async def test_summary_uses_last_seen_at_for_new_posts(self):
        """summary() uses user.last_seen_at as the cutoff for new_posts count."""
        last_seen = NOW - timedelta(hours=2)
        user = _make_user(last_seen_at=last_seen)

        post_repo = AsyncMock(spec=PostRepository)
        post_repo.count_new_since.return_value = 7

        event_repo = AsyncMock(spec=EventRepository)
        event_repo.list_in_range.return_value = []

        notification_repo = AsyncMock(spec=NotificationRepository)
        notification_repo.get_unread_count.return_value = 3

        subgroup_repo = AsyncMock(spec=SubgroupRepository)
        subgroup_repo.list_visible_for_user.return_value = []

        svc = _build_service(
            post_repo=post_repo,
            event_repo=event_repo,
            notification_repo=notification_repo,
            subgroup_repo=subgroup_repo,
        )
        result = await svc.summary(user=user, now=NOW)

        assert result.new_posts == 7
        post_repo.count_new_since.assert_awaited_once_with(
            community_id=COMMUNITY_ID,
            viewer_id=USER_ID,
            since=last_seen,
            subgroup_ids=[],
        )

    @pytest.mark.asyncio
    async def test_summary_falls_back_to_24h_when_no_last_seen(self):
        """summary() falls back to now-24h when user.last_seen_at is None."""
        user = _make_user(last_seen_at=None)

        post_repo = AsyncMock(spec=PostRepository)
        post_repo.count_new_since.return_value = 2

        event_repo = AsyncMock(spec=EventRepository)
        event_repo.list_in_range.return_value = []

        notification_repo = AsyncMock(spec=NotificationRepository)
        notification_repo.get_unread_count.return_value = 0

        subgroup_repo = AsyncMock(spec=SubgroupRepository)
        subgroup_repo.list_visible_for_user.return_value = []

        svc = _build_service(
            post_repo=post_repo,
            event_repo=event_repo,
            notification_repo=notification_repo,
            subgroup_repo=subgroup_repo,
        )
        result = await svc.summary(user=user, now=NOW)

        assert result.new_posts == 2
        expected_since = NOW - timedelta(hours=24)
        post_repo.count_new_since.assert_awaited_once_with(
            community_id=COMMUNITY_ID,
            viewer_id=USER_ID,
            since=expected_since,
            subgroup_ids=[],
        )

    @pytest.mark.asyncio
    async def test_summary_counts_upcoming_events(self):
        """summary() returns upcoming_events count from event_repo.list_in_range."""
        user = _make_user()

        post_repo = AsyncMock(spec=PostRepository)
        post_repo.count_new_since.return_value = 0

        event_repo = AsyncMock(spec=EventRepository)
        event1 = MagicMock(spec=Event)
        event2 = MagicMock(spec=Event)
        event_repo.list_in_range.return_value = [event1, event2]

        notification_repo = AsyncMock(spec=NotificationRepository)
        notification_repo.get_unread_count.return_value = 0

        subgroup_repo = AsyncMock(spec=SubgroupRepository)
        subgroup_repo.list_visible_for_user.return_value = []

        svc = _build_service(
            post_repo=post_repo,
            event_repo=event_repo,
            notification_repo=notification_repo,
            subgroup_repo=subgroup_repo,
        )
        result = await svc.summary(user=user, now=NOW)

        assert result.upcoming_events == 2
        event_repo.list_in_range.assert_awaited_once()
        call_kwargs = event_repo.list_in_range.call_args
        assert call_kwargs.kwargs["start"] == NOW
        assert call_kwargs.kwargs["end"] == NOW + timedelta(days=7)
        assert call_kwargs.kwargs["viewer_id"] == USER_ID

    @pytest.mark.asyncio
    async def test_summary_counts_unread_notifications(self):
        """summary() returns unread_notifications from notification_repo."""
        user = _make_user()

        post_repo = AsyncMock(spec=PostRepository)
        post_repo.count_new_since.return_value = 0

        event_repo = AsyncMock(spec=EventRepository)
        event_repo.list_in_range.return_value = []

        notification_repo = AsyncMock(spec=NotificationRepository)
        notification_repo.get_unread_count.return_value = 5

        subgroup_repo = AsyncMock(spec=SubgroupRepository)
        subgroup_repo.list_visible_for_user.return_value = []

        svc = _build_service(
            post_repo=post_repo,
            event_repo=event_repo,
            notification_repo=notification_repo,
            subgroup_repo=subgroup_repo,
        )
        result = await svc.summary(user=user, now=NOW)

        assert result.unread_notifications == 5
        notification_repo.get_unread_count.assert_awaited_once_with(USER_ID)

    @pytest.mark.asyncio
    async def test_summary_all_zeros_when_empty(self):
        """summary() returns zeros when all repos return empty/zero."""
        user = _make_user()

        post_repo = AsyncMock(spec=PostRepository)
        post_repo.count_new_since.return_value = 0

        event_repo = AsyncMock(spec=EventRepository)
        event_repo.list_in_range.return_value = []

        notification_repo = AsyncMock(spec=NotificationRepository)
        notification_repo.get_unread_count.return_value = 0

        subgroup_repo = AsyncMock(spec=SubgroupRepository)
        subgroup_repo.list_visible_for_user.return_value = []

        svc = _build_service(
            post_repo=post_repo,
            event_repo=event_repo,
            notification_repo=notification_repo,
            subgroup_repo=subgroup_repo,
        )
        result = await svc.summary(user=user, now=NOW)

        assert result.new_posts == 0
        assert result.upcoming_events == 0
        assert result.unread_notifications == 0


class TestSummaryVisibilityScoping:
    """@brief Tests that summary() passes subgroup_ids to count_new_since."""

    @pytest.mark.asyncio
    async def test_summary_resolves_subgroup_ids_and_passes_to_count_new_since(self):
        """summary() should resolve subgroups via subgroup_repo and pass ids to count_new_since."""
        user = _make_user(last_seen_at=NOW - timedelta(hours=1))
        sg1 = _make_subgroup()
        sg2 = _make_subgroup()

        post_repo = AsyncMock(spec=PostRepository)
        post_repo.count_new_since.return_value = 3

        event_repo = AsyncMock(spec=EventRepository)
        event_repo.list_in_range.return_value = []

        notification_repo = AsyncMock(spec=NotificationRepository)
        notification_repo.get_unread_count.return_value = 0

        subgroup_repo = AsyncMock(spec=SubgroupRepository)
        subgroup_repo.list_visible_for_user.return_value = [sg1, sg2]

        svc = _build_service(
            post_repo=post_repo,
            event_repo=event_repo,
            notification_repo=notification_repo,
            subgroup_repo=subgroup_repo,
        )
        result = await svc.summary(user=user, now=NOW)

        assert result.new_posts == 3
        subgroup_repo.list_visible_for_user.assert_awaited_once_with(COMMUNITY_ID, USER_ID)
        call_kwargs = post_repo.count_new_since.call_args
        assert call_kwargs.kwargs["subgroup_ids"] == [sg1.id, sg2.id]
        assert call_kwargs.kwargs["viewer_id"] == USER_ID

    @pytest.mark.asyncio
    async def test_summary_zero_subgroups_passes_empty_list_to_count_new_since(self):
        """summary() passes subgroup_ids=[] when user belongs to no subgroups."""
        user = _make_user(last_seen_at=NOW - timedelta(hours=1))

        post_repo = AsyncMock(spec=PostRepository)
        post_repo.count_new_since.return_value = 1

        event_repo = AsyncMock(spec=EventRepository)
        event_repo.list_in_range.return_value = []

        notification_repo = AsyncMock(spec=NotificationRepository)
        notification_repo.get_unread_count.return_value = 0

        subgroup_repo = AsyncMock(spec=SubgroupRepository)
        subgroup_repo.list_visible_for_user.return_value = []

        svc = _build_service(
            post_repo=post_repo,
            event_repo=event_repo,
            notification_repo=notification_repo,
            subgroup_repo=subgroup_repo,
        )
        result = await svc.summary(user=user, now=NOW)

        assert result.new_posts == 1
        call_kwargs = post_repo.count_new_since.call_args
        assert call_kwargs.kwargs["subgroup_ids"] == []
        assert call_kwargs.kwargs["viewer_id"] == USER_ID


class TestListMedia:
    """@brief Tests for HomeService.list_media()."""

    @pytest.mark.asyncio
    async def test_list_media_returns_empty_when_no_subgroups_and_no_community_media(
        self,
    ):
        """list_media() returns empty list when user has no subgroups and no media."""
        user = _make_user()

        subgroup_repo = AsyncMock(spec=SubgroupRepository)
        subgroup_repo.list_visible_for_user.return_value = []

        media_repo = AsyncMock(spec=SubgroupMediaRepository)
        media_repo.list_media.return_value = ([], None)

        svc = _build_service(subgroup_repo=subgroup_repo, media_repo=media_repo)
        items, next_cursor = await svc.list_media(user=user, limit=24)

        assert items == []
        assert next_cursor is None

    @pytest.mark.asyncio
    async def test_list_media_aggregates_across_user_subgroups(self):
        """list_media() calls media_repo for each subgroup and aggregates."""
        user = _make_user()
        sg1 = _make_subgroup(name="Alpha")
        sg2 = _make_subgroup(name="Beta")

        subgroup_repo = AsyncMock(spec=SubgroupRepository)
        subgroup_repo.list_visible_for_user.return_value = [sg1, sg2]

        item_a = {
            "media_id": str(uuid.uuid4()),
            "source": "post",
            "created_at": "2026-04-28T10:00:00",
        }
        item_b = {
            "media_id": str(uuid.uuid4()),
            "source": "gallery",
            "created_at": "2026-04-27T10:00:00",
        }

        media_repo = AsyncMock(spec=SubgroupMediaRepository)
        media_repo.list_media.side_effect = [
            ([item_a], None),
            ([item_b], None),
        ]

        svc = _build_service(subgroup_repo=subgroup_repo, media_repo=media_repo)
        items, next_cursor = await svc.list_media(user=user, limit=24)

        assert len(items) == 2
        assert media_repo.list_media.await_count == 2

    @pytest.mark.asyncio
    async def test_list_media_respects_limit(self):
        """list_media() truncates total results to limit."""
        user = _make_user()
        sg = _make_subgroup()

        subgroup_repo = AsyncMock(spec=SubgroupRepository)
        subgroup_repo.list_visible_for_user.return_value = [sg]

        items_data = [
            {
                "media_id": str(uuid.uuid4()),
                "source": "post",
                "created_at": f"2026-04-{i:02d}T10:00:00",
            }
            for i in range(1, 11)
        ]
        media_repo = AsyncMock(spec=SubgroupMediaRepository)
        media_repo.list_media.return_value = (items_data, None)

        svc = _build_service(subgroup_repo=subgroup_repo, media_repo=media_repo)
        items, _ = await svc.list_media(user=user, limit=5)

        assert len(items) <= 5
