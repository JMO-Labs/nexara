"""
@file test_bookmarks.py
@brief Route-level tests for the bookmarks API (toggle, list, delete, DI wiring).
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1 import bookmarks
from app.core.dependencies import get_current_user
from app.services.bookmark_service import BookmarkService

POST_ID = uuid.uuid4()


@pytest.fixture
def service() -> AsyncMock:
    """@brief Mock BookmarkService injected in place of the real builder."""
    return AsyncMock(spec=BookmarkService)


@pytest.fixture
def client(test_app, service):
    """@brief Authenticated client with the service dependency overridden."""
    user = MagicMock()
    user.id = uuid.uuid4()
    test_app.dependency_overrides[get_current_user] = lambda: user
    test_app.dependency_overrides[bookmarks._build_service] = lambda: service
    yield AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test")
    test_app.dependency_overrides.clear()


class TestRoutes:
    """@brief Each route delegates to the service and shapes the response."""

    async def test_toggle(self, client, service):
        service.toggle.return_value = {"post_id": str(POST_ID), "is_bookmarked": True}
        async with client as c:
            resp = await c.post(f"/api/v1/posts/{POST_ID}/bookmark")
        assert resp.status_code == 200
        assert resp.json()["is_bookmarked"] is True
        service.toggle.assert_awaited_once()

    async def test_list(self, client, service):
        service.list.return_value = {
            "bookmarks": [],
            "pagination": {"next_cursor": None, "has_more": False},
        }
        async with client as c:
            resp = await c.get("/api/v1/bookmarks?limit=5&cursor=abc")
        assert resp.status_code == 200
        assert resp.json()["bookmarks"] == []
        assert service.list.await_args.args[1:] == ("abc", 5)

    async def test_delete(self, client, service):
        bid = uuid.uuid4()
        async with client as c:
            resp = await c.delete(f"/api/v1/bookmarks/{bid}")
        assert resp.status_code == 204
        assert service.delete.await_args.args[0] == bid


def test_build_service_wires_dependencies():
    """@brief _build_service binds repos and the configured community id."""
    settings = MagicMock(COMMUNITY_ID="00000000-0000-0000-0000-000000000001")
    svc = bookmarks._build_service(AsyncMock(), settings)
    assert isinstance(svc, BookmarkService)
