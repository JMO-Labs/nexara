"""
@file test_event_repo_aggregated.py
@brief Unit tests for EventRepository community-level scope aggregation (Phase 4).

Tests for list_in_range with visibility union of community-root + subgroup events.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.event import Event
from app.repositories.event_repo import EventRepository

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
VIEWER_ID = uuid.uuid4()
AUTHOR_ID = uuid.uuid4()
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


class TestEventRepositoryVisibilityUnion:
    """@brief Tests for EventRepository.list_in_range() visibility union (Phase 4)."""

    @pytest.mark.asyncio
    async def test_list_in_range_filters_community_visible_requires_null_subgroup(self):
        """
        list_in_range() visibility predicate requires community-visible events
        to have subgroup_id IS NULL (not just visibility='community').
        """
        session = _make_session()
        now = datetime.now(UTC)
        start = now - timedelta(days=7)
        end = now + timedelta(days=90)

        # Create a mock event with visibility='community' and NULL subgroup_id
        event = MagicMock(spec=Event)
        event.id = uuid.uuid4()
        event.author_id = AUTHOR_ID
        event.visibility = "community"
        event.subgroup_id = None  # Community-root
        event.starts_at = now + timedelta(days=1)
        event.ends_at = now + timedelta(days=1, hours=2)
        event.recurrence_rule = None

        # Mock the result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [event]
        session.execute = AsyncMock(return_value=mock_result)

        repo = EventRepository(session)
        events = await repo.list_in_range(
            COMMUNITY_ID,
            start=start,
            end=end,
            viewer_id=VIEWER_ID,
            subgroup_ids=[SG_ID_1, SG_ID_2],
        )

        assert len(events) == 1
        assert events[0].visibility == "community"
        assert events[0].subgroup_id is None

    @pytest.mark.asyncio
    async def test_list_in_range_filters_subgroup_visible_by_membership(self):
        """
        list_in_range() visibility predicate includes subgroup-visible events
        only when viewer belongs to that subgroup.
        """
        session = _make_session()
        now = datetime.now(UTC)
        start = now - timedelta(days=7)
        end = now + timedelta(days=90)

        # Create a mock event with visibility='subgroup' and SG_ID_1
        event = MagicMock(spec=Event)
        event.id = uuid.uuid4()
        event.author_id = AUTHOR_ID
        event.visibility = "subgroup"
        event.subgroup_id = SG_ID_1  # Viewer belongs to this subgroup
        event.starts_at = now + timedelta(days=1)
        event.ends_at = now + timedelta(days=1, hours=2)
        event.recurrence_rule = None

        # Mock the result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [event]
        session.execute = AsyncMock(return_value=mock_result)

        repo = EventRepository(session)
        events = await repo.list_in_range(
            COMMUNITY_ID,
            start=start,
            end=end,
            viewer_id=VIEWER_ID,
            subgroup_ids=[SG_ID_1, SG_ID_2],  # Viewer in SG_ID_1
        )

        assert len(events) == 1
        assert events[0].visibility == "subgroup"
        assert events[0].subgroup_id == SG_ID_1

    @pytest.mark.asyncio
    async def test_list_in_range_filters_private_only_for_author(self):
        """
        list_in_range() visibility predicate restricts private events to author only.
        """
        session = _make_session()
        now = datetime.now(UTC)
        start = now - timedelta(days=7)
        end = now + timedelta(days=90)

        # Create a mock private event
        event = MagicMock(spec=Event)
        event.id = uuid.uuid4()
        event.author_id = VIEWER_ID  # Viewer is the author
        event.visibility = "private"
        event.subgroup_id = None
        event.starts_at = now + timedelta(days=1)
        event.ends_at = now + timedelta(days=1, hours=2)
        event.recurrence_rule = None

        # Mock the result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [event]
        session.execute = AsyncMock(return_value=mock_result)

        repo = EventRepository(session)
        events = await repo.list_in_range(
            COMMUNITY_ID,
            start=start,
            end=end,
            viewer_id=VIEWER_ID,
            subgroup_ids=[SG_ID_1],
        )

        assert len(events) == 1
        assert events[0].visibility == "private"
        assert events[0].author_id == VIEWER_ID
