"""
@file test_event_repo_subscription.py
@brief Unit tests for EventRepository.update_subscription.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from app.models.event import CalendarSubscription
from app.repositories.event_repo import EventRepository


class TestUpdateSubscription:
    """@brief update_subscription flushes, refreshes and returns the row."""

    async def test_flushes_refreshes_and_returns(self):
        session = AsyncMock()
        sub = MagicMock(spec=CalendarSubscription)
        repo = EventRepository(session)

        result = await repo.update_subscription(sub)

        session.flush.assert_awaited_once()
        session.refresh.assert_awaited_once_with(sub)
        assert result is sub
