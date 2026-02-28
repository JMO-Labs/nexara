"""
@file test_posts_endpoints.py
@brief Unit tests for posts API endpoints using httpx AsyncClient.

Tests exercise feed, CRUD, comments, and reactions with mocked
PostService and authentication dependencies.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1 import posts as posts_module
from app.core.dependencies import get_current_user


def _mock_user(**overrides) -> MagicMock:
    """@brief Build a mock User for dependency injection."""
    user = MagicMock()
    user.id = overrides.get("id", uuid.uuid4())
    user.community_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    user.username = overrides.get("username", "testuser")
    user.display_name = overrides.get("display_name", "Test User")
    user.avatar_url = None
    user.role = overrides.get("role", "member")
    return user


def _setup_auth_and_service(test_app, mock_service: AsyncMock):
    """@brief Override get_current_user and _build_service for authenticated tests."""
    user = _mock_user()

    async def _override_user():
        return user

    def _override_service():
        return mock_service

    test_app.dependency_overrides[get_current_user] = _override_user
    test_app.dependency_overrides[posts_module._build_service] = _override_service
    return user


def _clear_overrides(test_app):
    """@brief Clear dependency overrides after each test."""
    test_app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_feed_authenticated(test_app):
    """@brief GET /posts returns 200 with items when authenticated."""
    mock_svc = AsyncMock()
    mock_svc.list_feed.return_value = {
        "items": [{"id": str(uuid.uuid4())}],
        "cursor": None,
        "has_more": False,
    }
    _setup_auth_and_service(test_app, mock_svc)
    try:
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/posts")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert isinstance(data["items"], list)
    finally:
        _clear_overrides(test_app)


@pytest.mark.asyncio
async def test_list_feed_unauthenticated(test_app):
    """@brief GET /posts returns 401 when not authenticated."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/posts")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_post_success(test_app):
    """@brief POST /posts with valid body returns 201."""
    mock_svc = AsyncMock()
    mock_svc.create_post.return_value = {"id": str(uuid.uuid4()), "content": "Hello"}
    _setup_auth_and_service(test_app, mock_svc)
    try:
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/v1/posts", json={"content": "Hello world"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["content"] == "Hello"
    finally:
        _clear_overrides(test_app)


@pytest.mark.asyncio
async def test_create_post_empty_content(test_app):
    """@brief POST /posts with empty content returns 422."""
    mock_svc = AsyncMock()
    _setup_auth_and_service(test_app, mock_svc)
    try:
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/v1/posts", json={"content": ""})
        assert resp.status_code == 422
    finally:
        _clear_overrides(test_app)


@pytest.mark.asyncio
async def test_get_post_success(test_app):
    """@brief GET /posts/{id} returns 200 when post exists."""
    post_id = uuid.uuid4()
    mock_svc = AsyncMock()
    mock_svc.get_post.return_value = {"id": str(post_id), "content": "Test post"}
    _setup_auth_and_service(test_app, mock_svc)
    try:
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/api/v1/posts/{post_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["content"] == "Test post"
    finally:
        _clear_overrides(test_app)


@pytest.mark.asyncio
async def test_get_post_not_found(test_app):
    """@brief GET /posts/{id} returns 404 when post does not exist."""
    from app.core.exceptions import NotFoundError

    post_id = uuid.uuid4()
    mock_svc = AsyncMock()
    mock_svc.get_post.side_effect = NotFoundError("Post not found")
    _setup_auth_and_service(test_app, mock_svc)
    try:
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/api/v1/posts/{post_id}")
        assert resp.status_code == 404
    finally:
        _clear_overrides(test_app)


@pytest.mark.asyncio
async def test_delete_post_success(test_app):
    """@brief DELETE /posts/{id} returns 200 when authorized."""
    post_id = uuid.uuid4()
    mock_svc = AsyncMock()
    mock_svc.delete_post.return_value = None
    _setup_auth_and_service(test_app, mock_svc)
    try:
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.delete(f"/api/v1/posts/{post_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "message" in data
    finally:
        _clear_overrides(test_app)


@pytest.mark.asyncio
async def test_list_comments_success(test_app):
    """@brief GET /posts/{id}/comments returns 200 with paginated comments."""
    post_id = uuid.uuid4()
    mock_svc = AsyncMock()
    mock_svc.list_comments.return_value = {
        "items": [{"id": str(uuid.uuid4()), "content": "A comment"}],
        "cursor": None,
        "has_more": False,
    }
    _setup_auth_and_service(test_app, mock_svc)
    try:
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/api/v1/posts/{post_id}/comments")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["items"], list)
        assert len(data["items"]) == 1
        assert data["items"][0]["content"] == "A comment"
        assert data["has_more"] is False
    finally:
        _clear_overrides(test_app)


@pytest.mark.asyncio
async def test_create_comment_success(test_app):
    """@brief POST /posts/{id}/comments returns 201 when valid."""
    post_id = uuid.uuid4()
    mock_svc = AsyncMock()
    mock_svc.add_comment.return_value = {"id": str(uuid.uuid4()), "content": "New comment"}
    _setup_auth_and_service(test_app, mock_svc)
    try:
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                f"/api/v1/posts/{post_id}/comments",
                json={"content": "New comment"},
            )
        assert resp.status_code == 201
        data = resp.json()
        assert data["content"] == "New comment"
    finally:
        _clear_overrides(test_app)


@pytest.mark.asyncio
async def test_toggle_reaction_success(test_app):
    """@brief POST /posts/{id}/reactions returns 200 with action and count."""
    post_id = uuid.uuid4()
    mock_svc = AsyncMock()
    mock_svc.toggle_reaction.return_value = {"action": "added", "emoji": "👍", "count": 1}
    _setup_auth_and_service(test_app, mock_svc)
    try:
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                f"/api/v1/posts/{post_id}/reactions",
                json={"emoji": "👍"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["action"] == "added"
        assert data["emoji"] == "👍"
        assert data["count"] == 1
    finally:
        _clear_overrides(test_app)
