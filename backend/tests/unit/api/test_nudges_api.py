"""
@file test_nudges_api.py
@brief Route and dependency-builder tests for POST /api/v1/nudges/{user_id}.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

from httpx import ASGITransport, AsyncClient

from app.api.v1 import nudges as nudges_module
from app.core.config import get_settings
from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.nudge_service import NudgeService


def test_build_service_wires_nudge_service():
    service = nudges_module._build_service(MagicMock(), get_settings())
    assert isinstance(service, NudgeService)


async def test_send_nudge_returns_201(test_app):
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    target = uuid.uuid4()
    service = AsyncMock()
    service.send.return_value = {
        "id": uuid.uuid4(),
        "sender_id": user.id,
        "target_id": target,
        "nudge_type": "user_initiated",
        "created_at": datetime.now(UTC),
    }
    test_app.dependency_overrides[get_current_user] = lambda: user
    test_app.dependency_overrides[nudges_module._build_service] = lambda: service
    try:
        async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as c:
            resp = await c.post(f"/api/v1/nudges/{target}")
    finally:
        test_app.dependency_overrides.clear()
    assert resp.status_code == 201
    service.send.assert_awaited_once_with(user, target)
