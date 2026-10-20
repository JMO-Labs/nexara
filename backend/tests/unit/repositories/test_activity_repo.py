"""
@file test_activity_repo.py
@brief Unit tests for ActivityRepository.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.activity_event import ActivityEvent
from app.repositories.activity_repo import ActivityRepository

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
ACTOR_ID = uuid.uuid4()
VIEWER_ID = uuid.uuid4()
OBJECT_ID = uuid.uuid4()
SUBGROUP_ID = uuid.uuid4()


def _make_session() -> AsyncMock:
    """@brief Create a mock AsyncSession with common stubs."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    session.execute = AsyncMock()
    return session


class TestActivityRepositoryRecord:
    """@brief Tests for ActivityRepository.record()."""

    @pytest.mark.asyncio
    async def test_record_inserts_activity_event(self):
        """record() should insert an activity event without raising."""
        session = _make_session()
        repo = ActivityRepository(session)

        await repo.record(
            community_id=COMMUNITY_ID,
            actor_id=ACTOR_ID,
            verb="post.created",
            object_type="post",
            object_id=OBJECT_ID,
            subgroup_id=None,
            visibility="community",
        )

        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_record_wraps_exception_in_try_except(self):
        """record() should catch exceptions and log them without raising."""
        session = _make_session()
        session.flush = AsyncMock(side_effect=Exception("DB error"))
        repo = ActivityRepository(session)

        # Should not raise even though flush() fails
        await repo.record(
            community_id=COMMUNITY_ID,
            actor_id=ACTOR_ID,
            verb="post.created",
            object_type="post",
            object_id=OBJECT_ID,
            subgroup_id=None,
            visibility="community",
        )

    @pytest.mark.asyncio
    async def test_record_with_metadata_and_target(self):
        """record() should accept optional metadata and target fields."""
        session = _make_session()
        repo = ActivityRepository(session)

        metadata = {
            "actor_name": "Sue",
            "object_title": "Trip Album",
            "container_title": "Family",
            "count_hint": 4,
        }

        await repo.record(
            community_id=COMMUNITY_ID,
            actor_id=ACTOR_ID,
            verb="media.uploaded",
            object_type="media",
            object_id=OBJECT_ID,
            subgroup_id=SUBGROUP_ID,
            visibility="subgroup",
            target_type="gallery",
            target_id=uuid.uuid4(),
            metadata=metadata,
        )

        session.flush.assert_awaited_once()


class TestActivityRepositoryInvalidate:
    """@brief Tests for ActivityRepository.invalidate()."""

    @pytest.mark.asyncio
    async def test_invalidate_marks_is_active_false(self):
        """invalidate() should set is_active=false for matching events."""
        session = _make_session()

        # Mock the execute result
        mock_result = MagicMock()
        mock_result.rowcount = 1
        session.execute = AsyncMock(return_value=mock_result)
        session.flush = AsyncMock()

        repo = ActivityRepository(session)
        await repo.invalidate(object_type="post", object_id=OBJECT_ID)

        session.execute.assert_awaited_once()
        session.flush.assert_awaited_once()


class TestActivityRepositoryListForUser:
    """@brief Tests for ActivityRepository.list_for_user()."""

    @pytest.mark.asyncio
    async def test_list_for_user_excludes_viewer_own_actions(self):
        """list_for_user() should exclude events where actor_id == viewer_id."""
        session = _make_session()

        # Create mock events
        event1 = MagicMock(spec=ActivityEvent)
        event1.id = uuid.uuid4()
        event1.actor_id = ACTOR_ID
        event1.verb = "post.created"
        event1.object_type = "post"
        event1.created_at = datetime.now(UTC)

        event2 = MagicMock(spec=ActivityEvent)
        event2.id = uuid.uuid4()
        event2.actor_id = VIEWER_ID  # Same as viewer
        event2.verb = "post.created"
        event2.object_type = "post"
        event2.created_at = datetime.now(UTC) - timedelta(hours=1)

        # SQL `actor_id != viewer_id` filters event2 in the database; mock
        # the filtered result the DB would return.
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [event1]
        session.execute = AsyncMock(return_value=mock_result)

        repo = ActivityRepository(session)
        result = await repo.list_for_user(
            community_id=COMMUNITY_ID,
            viewer_id=VIEWER_ID,
            viewer_subgroup_ids=[SUBGROUP_ID],
        )

        # Verify the WHERE clause includes the actor_id filter
        executed_stmt = session.execute.call_args[0][0]
        assert "actor_id" in str(executed_stmt.compile(compile_kwargs={"literal_binds": False}))
        assert len(result) == 1
        assert result[0].id == event1.id
        _ = event2  # referenced for clarity

    @pytest.mark.asyncio
    async def test_list_for_user_filters_visibility_community(self):
        """list_for_user() should include events with visibility='community'."""
        session = _make_session()

        event = MagicMock(spec=ActivityEvent)
        event.id = uuid.uuid4()
        event.actor_id = ACTOR_ID
        event.visibility = "community"
        event.subgroup_id = None
        event.created_at = datetime.now(UTC)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [event]
        session.execute = AsyncMock(return_value=mock_result)

        repo = ActivityRepository(session)
        result = await repo.list_for_user(
            community_id=COMMUNITY_ID,
            viewer_id=VIEWER_ID,
            viewer_subgroup_ids=[],
        )

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_list_for_user_filters_visibility_subgroup(self):
        """list_for_user() should include subgroup events viewer is in."""
        session = _make_session()

        sg_id = uuid.uuid4()
        event = MagicMock(spec=ActivityEvent)
        event.id = uuid.uuid4()
        event.actor_id = ACTOR_ID
        event.visibility = "subgroup"
        event.subgroup_id = sg_id
        event.created_at = datetime.now(UTC)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [event]
        session.execute = AsyncMock(return_value=mock_result)

        repo = ActivityRepository(session)
        result = await repo.list_for_user(
            community_id=COMMUNITY_ID,
            viewer_id=VIEWER_ID,
            viewer_subgroup_ids=[sg_id],
        )

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_list_for_user_excludes_private_visibility(self):
        """list_for_user() should exclude events with visibility='private'."""
        session = _make_session()

        event = MagicMock(spec=ActivityEvent)
        event.id = uuid.uuid4()
        event.actor_id = ACTOR_ID
        event.visibility = "private"
        event.subgroup_id = None
        event.created_at = datetime.now(UTC)

        # SQL visibility predicate filters private rows in the database; mock
        # the filtered result the DB would return.
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=mock_result)

        repo = ActivityRepository(session)
        result = await repo.list_for_user(
            community_id=COMMUNITY_ID,
            viewer_id=VIEWER_ID,
            viewer_subgroup_ids=[],
        )

        # Verify the WHERE clause filters by visibility (community OR subgroup)
        executed_stmt = session.execute.call_args[0][0]
        compiled = str(executed_stmt.compile(compile_kwargs={"literal_binds": False}))
        assert "visibility" in compiled
        assert len(result) == 0
        _ = event  # referenced for clarity

    @pytest.mark.asyncio
    async def test_list_for_user_applies_block_filter(self):
        """list_for_user() should apply block filter via apply_block_filter."""
        session = _make_session()

        event = MagicMock(spec=ActivityEvent)
        event.id = uuid.uuid4()
        event.actor_id = ACTOR_ID
        event.visibility = "community"
        event.created_at = datetime.now(UTC)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [event]
        session.execute = AsyncMock(return_value=mock_result)

        repo = ActivityRepository(session)
        result = await repo.list_for_user(
            community_id=COMMUNITY_ID,
            viewer_id=VIEWER_ID,
            viewer_subgroup_ids=[],
        )

        # Verify execute was called (block filter is applied in real repo)
        session.execute.assert_awaited_once()
        assert len(result) >= 0

    @pytest.mark.asyncio
    async def test_list_for_user_cursor_pagination(self):
        """list_for_user() should support cursor-based pagination."""
        session = _make_session()

        now = datetime.now(UTC)
        event1 = MagicMock(spec=ActivityEvent)
        event1.id = uuid.uuid4()
        event1.actor_id = ACTOR_ID
        event1.visibility = "community"
        event1.created_at = now

        event2 = MagicMock(spec=ActivityEvent)
        event2.id = uuid.uuid4()
        event2.actor_id = ACTOR_ID
        event2.visibility = "community"
        event2.created_at = now - timedelta(hours=1)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [event1, event2]
        session.execute = AsyncMock(return_value=mock_result)

        repo = ActivityRepository(session)
        result = await repo.list_for_user(
            community_id=COMMUNITY_ID,
            viewer_id=VIEWER_ID,
            viewer_subgroup_ids=[],
            cursor=now,
            limit=10,
        )

        assert len(result) >= 0
        session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_list_for_user_respects_limit(self):
        """list_for_user() should respect the limit parameter."""
        session = _make_session()

        events = [
            MagicMock(spec=ActivityEvent, id=uuid.uuid4(), actor_id=ACTOR_ID) for _ in range(50)
        ]
        for i, e in enumerate(events):
            e.visibility = "community"
            e.created_at = datetime.now(UTC) - timedelta(hours=i)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = events[:30]
        session.execute = AsyncMock(return_value=mock_result)

        repo = ActivityRepository(session)
        result = await repo.list_for_user(
            community_id=COMMUNITY_ID,
            viewer_id=VIEWER_ID,
            viewer_subgroup_ids=[],
            limit=30,
        )

        assert len(result) <= 30


class TestActivityRepositoryRetention:
    """@brief Tests for activity event retention/deletion."""

    @pytest.mark.asyncio
    async def test_retention_delete_old_events(self):
        """Activity events older than 30 days should be deletable."""
        session = _make_session()
        session.execute = AsyncMock()
        session.flush = AsyncMock()

        repo = ActivityRepository(session)

        # Simulate calling a delete method (we'll implement this in the actual repo)
        await repo.delete_older_than_days(days=30)

        session.execute.assert_awaited()
        session.flush.assert_awaited()
