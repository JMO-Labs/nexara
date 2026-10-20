"""
@file test_activity_service.py
@brief Unit tests for ActivityService: aggregation, filtering, existence check.

Tests for read-time aggregation (60-min window), dead-object filtering, and
own-action exclusion.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.activity_event import ActivityEvent
from app.models.user import User
from app.repositories.activity_repo import ActivityRepository
from app.repositories.event_repo import EventRepository
from app.repositories.gallery_repo import GalleryRepository
from app.repositories.post_repo import PostRepository
from app.repositories.subgroup_media_repo import SubgroupMediaRepository
from app.repositories.subgroup_repo import SubgroupRepository
from app.schemas.activity import ActivityFeedResponse

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
VIEWER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
ACTOR_ID = uuid.UUID("00000000-0000-0000-0000-000000000003")
BASE_TIME = datetime(2026, 4, 30, 12, 0, 0, tzinfo=UTC)


def _make_user(user_id=VIEWER_ID) -> MagicMock:
    """@brief Build a mock User."""
    user = MagicMock(spec=User)
    user.id = user_id
    user.community_id = COMMUNITY_ID
    user.display_name = "Test User"
    return user


def _make_activity_event(
    event_id: uuid.UUID,
    actor_id: uuid.UUID,
    verb: str,
    object_type: str,
    object_id: uuid.UUID,
    created_at: datetime,
    count_hint: int = 1,
) -> ActivityEvent:
    """@brief Construct an ActivityEvent for testing."""
    event = MagicMock(spec=ActivityEvent)
    event.id = event_id
    event.actor_id = actor_id
    event.verb = verb
    event.object_type = object_type
    event.object_id = object_id
    event.target_type = "community"
    event.target_id = COMMUNITY_ID
    event.subgroup_id = None
    event.visibility = "community"
    event.created_at = created_at
    event.event_metadata = {
        "actor_name": "Sue",
        "object_title": "Trip Album",
        "container_title": "Family",
        "count_hint": count_hint,
    }
    return event


def _build_service(
    activity_repo: AsyncMock | None = None,
    subgroup_repo: AsyncMock | None = None,
    post_repo: AsyncMock | None = None,
    event_repo: AsyncMock | None = None,
    gallery_repo: AsyncMock | None = None,
    media_repo: AsyncMock | None = None,
):
    """@brief Construct ActivityService with mocked repos."""
    from app.services.activity_service import ActivityService

    return ActivityService(
        activity_repo=activity_repo or AsyncMock(spec=ActivityRepository),
        subgroup_repo=subgroup_repo or AsyncMock(spec=SubgroupRepository),
        post_repo=post_repo or AsyncMock(spec=PostRepository),
        event_repo=event_repo or AsyncMock(spec=EventRepository),
        gallery_repo=gallery_repo or AsyncMock(spec=GalleryRepository),
        media_repo=media_repo or AsyncMock(spec=SubgroupMediaRepository),
        community_id=COMMUNITY_ID,
    )


class TestActivityServiceAggregation:
    """@brief Tests for read-time aggregation logic."""

    @pytest.mark.asyncio
    async def test_aggregation_4_photos_within_60min(self):
        """4 photos within 60 min → 1 item with count=4."""
        user = _make_user()
        subgroup_repo = AsyncMock(spec=SubgroupRepository)
        subgroup_repo.list_visible_for_user.return_value = []

        # 4 media.uploaded events, last one is newest
        event_ids = [uuid.uuid4() for _ in range(4)]
        events = [
            _make_activity_event(
                event_ids[0],
                ACTOR_ID,
                "media.uploaded",
                "media",
                uuid.uuid4(),
                BASE_TIME - timedelta(minutes=50),
            ),
            _make_activity_event(
                event_ids[1],
                ACTOR_ID,
                "media.uploaded",
                "media",
                uuid.uuid4(),
                BASE_TIME - timedelta(minutes=40),
            ),
            _make_activity_event(
                event_ids[2],
                ACTOR_ID,
                "media.uploaded",
                "media",
                uuid.uuid4(),
                BASE_TIME - timedelta(minutes=20),
            ),
            _make_activity_event(
                event_ids[3],
                ACTOR_ID,
                "media.uploaded",
                "media",
                uuid.uuid4(),
                BASE_TIME,
            ),
        ]

        activity_repo = AsyncMock(spec=ActivityRepository)
        activity_repo.list_for_user.return_value = events

        # All repos confirm existence
        post_repo = AsyncMock(spec=PostRepository)
        event_repo = AsyncMock(spec=EventRepository)
        gallery_repo = AsyncMock(spec=GalleryRepository)
        media_repo = AsyncMock(spec=SubgroupMediaRepository)

        post_repo.exists_many.return_value = set()
        event_repo.exists_many.return_value = set()
        gallery_repo.exists_many.return_value = set()
        media_repo.exists_many.return_value = {events[i].object_id for i in range(4)}

        svc = _build_service(
            activity_repo=activity_repo,
            subgroup_repo=subgroup_repo,
            post_repo=post_repo,
            event_repo=event_repo,
            gallery_repo=gallery_repo,
            media_repo=media_repo,
        )

        result = await svc.list_for_user(user, cursor=None, limit=30)

        assert isinstance(result, ActivityFeedResponse)
        assert len(result.items) == 1
        assert result.items[0].count == 4
        assert result.items[0].id == event_ids[3]
        assert result.items[0].created_at == BASE_TIME
        assert result.next_cursor is None

    @pytest.mark.asyncio
    async def test_aggregation_4_photos_more_than_60min_apart(self):
        """4 photos >60 min apart → 4 separate items."""
        user = _make_user()
        subgroup_repo = AsyncMock(spec=SubgroupRepository)
        subgroup_repo.list_visible_for_user.return_value = []

        event_ids = [uuid.uuid4() for _ in range(4)]
        events = [
            _make_activity_event(
                event_ids[0],
                ACTOR_ID,
                "media.uploaded",
                "media",
                uuid.uuid4(),
                BASE_TIME - timedelta(hours=3),
            ),
            _make_activity_event(
                event_ids[1],
                ACTOR_ID,
                "media.uploaded",
                "media",
                uuid.uuid4(),
                BASE_TIME - timedelta(hours=2),
            ),
            _make_activity_event(
                event_ids[2],
                ACTOR_ID,
                "media.uploaded",
                "media",
                uuid.uuid4(),
                BASE_TIME - timedelta(hours=1),
            ),
            _make_activity_event(
                event_ids[3],
                ACTOR_ID,
                "media.uploaded",
                "media",
                uuid.uuid4(),
                BASE_TIME,
            ),
        ]

        activity_repo = AsyncMock(spec=ActivityRepository)
        activity_repo.list_for_user.return_value = events

        post_repo = AsyncMock(spec=PostRepository)
        event_repo = AsyncMock(spec=EventRepository)
        gallery_repo = AsyncMock(spec=GalleryRepository)
        media_repo = AsyncMock(spec=SubgroupMediaRepository)

        post_repo.exists_many.return_value = set()
        event_repo.exists_many.return_value = set()
        gallery_repo.exists_many.return_value = set()
        media_repo.exists_many.return_value = {events[i].object_id for i in range(4)}

        svc = _build_service(
            activity_repo=activity_repo,
            subgroup_repo=subgroup_repo,
            post_repo=post_repo,
            event_repo=event_repo,
            gallery_repo=gallery_repo,
            media_repo=media_repo,
        )

        result = await svc.list_for_user(user, cursor=None, limit=30)

        assert len(result.items) == 4
        assert all(item.count == 1 for item in result.items)

    @pytest.mark.asyncio
    async def test_dead_object_filter(self):
        """Events whose object doesn't exist are dropped."""
        user = _make_user()
        subgroup_repo = AsyncMock(spec=SubgroupRepository)
        subgroup_repo.list_visible_for_user.return_value = []

        post_id = uuid.uuid4()
        media_id = uuid.uuid4()

        events = [
            _make_activity_event(
                uuid.uuid4(),
                ACTOR_ID,
                "post.created",
                "post",
                post_id,
                BASE_TIME,
            ),
            _make_activity_event(
                uuid.uuid4(),
                ACTOR_ID,
                "media.uploaded",
                "media",
                media_id,
                BASE_TIME - timedelta(minutes=1),
            ),
        ]

        activity_repo = AsyncMock(spec=ActivityRepository)
        activity_repo.list_for_user.return_value = events

        post_repo = AsyncMock(spec=PostRepository)
        event_repo = AsyncMock(spec=EventRepository)
        gallery_repo = AsyncMock(spec=GalleryRepository)
        media_repo = AsyncMock(spec=SubgroupMediaRepository)

        # Post doesn't exist, media does
        post_repo.exists_many.return_value = set()
        event_repo.exists_many.return_value = set()
        gallery_repo.exists_many.return_value = set()
        media_repo.exists_many.return_value = {media_id}

        svc = _build_service(
            activity_repo=activity_repo,
            subgroup_repo=subgroup_repo,
            post_repo=post_repo,
            event_repo=event_repo,
            gallery_repo=gallery_repo,
            media_repo=media_repo,
        )

        result = await svc.list_for_user(user, cursor=None, limit=30)

        # Only media event remains
        assert len(result.items) == 1
        assert result.items[0].object_type == "media"
        assert result.items[0].object_id == media_id

    @pytest.mark.asyncio
    async def test_cursor_pagination(self):
        """next_cursor set when result length == limit."""
        user = _make_user()
        subgroup_repo = AsyncMock(spec=SubgroupRepository)
        subgroup_repo.list_visible_for_user.return_value = []

        events = []
        for i in range(30):
            ev = _make_activity_event(
                uuid.uuid4(),
                ACTOR_ID,
                "post.created",
                "post",
                uuid.uuid4(),
                BASE_TIME - timedelta(minutes=i),
            )
            # Distinct target per event so aggregation does not collapse them
            ev.target_id = uuid.uuid4()
            events.append(ev)

        activity_repo = AsyncMock(spec=ActivityRepository)
        activity_repo.list_for_user.return_value = events

        post_repo = AsyncMock(spec=PostRepository)
        event_repo = AsyncMock(spec=EventRepository)
        gallery_repo = AsyncMock(spec=GalleryRepository)
        media_repo = AsyncMock(spec=SubgroupMediaRepository)

        post_repo.exists_many.return_value = {e.object_id for e in events}
        event_repo.exists_many.return_value = set()
        gallery_repo.exists_many.return_value = set()
        media_repo.exists_many.return_value = set()

        svc = _build_service(
            activity_repo=activity_repo,
            subgroup_repo=subgroup_repo,
            post_repo=post_repo,
            event_repo=event_repo,
            gallery_repo=gallery_repo,
            media_repo=media_repo,
        )

        result = await svc.list_for_user(user, cursor=None, limit=30)

        # All 30 items returned, next_cursor should be the oldest created_at
        assert len(result.items) == 30
        assert result.next_cursor == events[-1].created_at

    @pytest.mark.asyncio
    async def test_next_cursor_none_when_fewer_items(self):
        """next_cursor is None when result length < limit."""
        user = _make_user()
        subgroup_repo = AsyncMock(spec=SubgroupRepository)
        subgroup_repo.list_visible_for_user.return_value = []

        events = []
        for i in range(15):
            ev = _make_activity_event(
                uuid.uuid4(),
                ACTOR_ID,
                "post.created",
                "post",
                uuid.uuid4(),
                BASE_TIME - timedelta(minutes=i),
            )
            ev.target_id = uuid.uuid4()
            events.append(ev)

        activity_repo = AsyncMock(spec=ActivityRepository)
        activity_repo.list_for_user.return_value = events

        post_repo = AsyncMock(spec=PostRepository)
        event_repo = AsyncMock(spec=EventRepository)
        gallery_repo = AsyncMock(spec=GalleryRepository)
        media_repo = AsyncMock(spec=SubgroupMediaRepository)

        post_repo.exists_many.return_value = {e.object_id for e in events}
        event_repo.exists_many.return_value = set()
        gallery_repo.exists_many.return_value = set()
        media_repo.exists_many.return_value = set()

        svc = _build_service(
            activity_repo=activity_repo,
            subgroup_repo=subgroup_repo,
            post_repo=post_repo,
            event_repo=event_repo,
            gallery_repo=gallery_repo,
            media_repo=media_repo,
        )

        result = await svc.list_for_user(user, cursor=None, limit=30)

        assert len(result.items) == 15
        assert result.next_cursor is None
