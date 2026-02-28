"""
@file conftest.py
@brief Shared fixtures for service unit tests.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.post import Post
from app.models.user import User
from app.repositories.post_repo import CommentRepository, PostRepository, ReactionRepository
from app.services.post_service import PostService

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
AUTHOR_ID = uuid.uuid4()
VIEWER_ID = uuid.uuid4()
ADMIN_ID = uuid.uuid4()
POST_ID = uuid.uuid4()


def _make_user(
    user_id: uuid.UUID | None = None,
    username: str = "alice",
    display_name: str = "Alice",
    role: str = "member",
) -> User:
    """@brief Create a mock User instance."""
    u = MagicMock(spec=User)
    u.id = user_id or AUTHOR_ID
    u.username = username
    u.display_name = display_name
    u.avatar_url = None
    u.role = role
    return u


def _make_post(author_id: uuid.UUID = AUTHOR_ID) -> Post:
    """@brief Create a mock Post instance."""
    p = MagicMock(spec=Post)
    p.id = POST_ID
    p.author_id = author_id
    return p


@pytest.fixture
def post_repo():
    """@brief Mock PostRepository."""
    return AsyncMock(spec=PostRepository)


@pytest.fixture
def comment_repo():
    """@brief Mock CommentRepository."""
    return AsyncMock(spec=CommentRepository)


@pytest.fixture
def reaction_repo():
    """@brief Mock ReactionRepository."""
    return AsyncMock(spec=ReactionRepository)


@pytest.fixture
def notification_svc():
    """@brief Mock NotificationService."""
    return AsyncMock()


@pytest.fixture
def feed_publisher():
    """@brief Mock feed_publisher coroutine."""
    return AsyncMock(return_value=1)


@pytest.fixture
def media_attacher():
    """@brief Mock media_attacher coroutine."""
    return AsyncMock()


@pytest.fixture
def service(post_repo, comment_repo, reaction_repo, notification_svc):
    """@brief PostService with mocked dependencies."""
    return PostService(
        post_repo=post_repo,
        comment_repo=comment_repo,
        reaction_repo=reaction_repo,
        notification_service=notification_svc,
        community_id=COMMUNITY_ID,
    )


@pytest.fixture
def service_with_publisher(service, feed_publisher):
    """@brief PostService with feed_publisher injected."""
    service._feed_publisher = feed_publisher
    return service


@pytest.fixture
def service_with_media(service, media_attacher):
    """@brief PostService with media_attacher injected."""
    service._media_attacher = media_attacher
    return service
