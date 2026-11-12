"""
@file test_calendar_subscription_update.py
@brief Route test: PUT /calendar-subscriptions/{id} delegates to the service.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

from httpx import ASGITransport, AsyncClient

from app.schemas.event import CalendarSubscriptionResponse

USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")


async def test_update_subscription_returns_service_result(test_app):
    from app.api.v1.events import _build_service
    from app.core.dependencies import get_current_user

    sub_id = uuid.uuid4()
    user = MagicMock()
    user.id = USER_ID
    user.is_active = True
    resp = CalendarSubscriptionResponse(
        id=sub_id,
        name="Renamed",
        color="#4285f4",
        source_type="ical_url",
        source_url="https://example.com/a.ics",
        visibility="private",
        sync_enabled=False,
        sync_interval_minutes=1440,
        last_synced_at=None,
        sync_error=None,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    service = AsyncMock()
    service.update_subscription.return_value = resp
    test_app.dependency_overrides[get_current_user] = lambda: user
    test_app.dependency_overrides[_build_service] = lambda: service

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        r = await client.put(
            f"/api/v1/calendar-subscriptions/{sub_id}",
            json={"name": "Renamed", "sync_enabled": False},
        )

    assert r.status_code == 200
    assert r.json()["name"] == "Renamed"
    args = service.update_subscription.await_args.args
    assert args[0] == sub_id and args[1] == USER_ID
    test_app.dependency_overrides.clear()
