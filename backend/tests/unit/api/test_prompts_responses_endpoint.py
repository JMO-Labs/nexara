"""
@file test_prompts_responses_endpoint.py
@brief Unit test for GET /prompts/posts/{id}/responses route.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1 import prompts as prompts_module
from app.core.dependencies import get_current_user


@pytest.mark.asyncio
async def test_list_responses_delegates_to_service(test_app):
    """@brief Route passes viewer, limit and cursor to the service and returns its payload."""
    user = MagicMock()
    user.id = uuid.uuid4()
    svc = AsyncMock()
    svc.list_responses.return_value = {"items": [], "cursor": None, "has_more": False}
    test_app.dependency_overrides[get_current_user] = lambda: user
    test_app.dependency_overrides[prompts_module._build_service] = lambda: svc
    pid = uuid.uuid4()
    try:
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            resp = await client.get(
                f"/api/v1/prompts/posts/{pid}/responses", params={"limit": 5, "cursor": "c"}
            )
    finally:
        test_app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert resp.json() == {"items": [], "cursor": None, "has_more": False}
    svc.list_responses.assert_awaited_once_with(pid, user.id, limit=5, cursor="c")
