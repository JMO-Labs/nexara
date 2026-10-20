"""
@file test_event_repo.py
@brief Unit tests for EventRepository.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.event import Event
from app.repositories.event_repo import EventRepository

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
AUTHOR_ID, EVENT_ID, VIEWER_ID = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()


def _make_session() -> AsyncMock:
    """@brief Create a mock AsyncSession with common stubs."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    return session


class TestEventRepositoryListInRange:
    """@brief Tests for EventRepository.list_in_range()."""

    @pytest.mark.asyncio
    async def test_filters_by_subgroup_id(self):
        """list_in_range should filter events by subgroup_id when provided."""
        session = _make_session()
        subgroup_id = uuid.uuid4()
        now = datetime.now(UTC)
        start = now - timedelta(days=7)
        end = now + timedelta(days=90)

        event = MagicMock(spec=Event)
        event.id = EVENT_ID
        event.author_id = AUTHOR_ID
        event.title = "Group Event"
        event.starts_at = now + timedelta(days=1)
        event.ends_at = now + timedelta(days=1, hours=2)
        event.visibility = "subgroup"
        event.subgroup_id = subgroup_id
        event.recurrence_rule = None

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [event]
        session.execute = AsyncMock(return_value=mock_result)

        repo = EventRepository(session)
        result = await repo.list_in_range(
            COMMUNITY_ID,
            start,
            end,
            viewer_id=VIEWER_ID,
            subgroup_ids=[subgroup_id],
        )

        assert len(result) == 1
        assert result[0].id == EVENT_ID
        assert result[0].subgroup_id == subgroup_id
        session.execute.assert_awaited_once()
