"""
@file test_search_service.py
@brief Unit tests for SearchService.

Tests search aggregation across posts, users, events, and comments
using mocked SearchRepository. Validates that raw queries are passed
through to the repository (websearch_to_tsquery handles sanitization).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from app.services.search_service import SearchService, build_prefix_tsquery

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


class TestBuildPrefixTsquery:
    """@brief Tests for build_prefix_tsquery()."""

    def test_single_word_gets_prefix_operator(self):
        """Single word should get :* appended."""
        assert build_prefix_tsquery("apple") == "apple:*"

    def test_multiple_words_joined_with_and(self):
        """Multiple words should be ANDed with :* on each."""
        assert build_prefix_tsquery("hello world") == "hello:* & world:*"

    def test_special_characters_stripped(self):
        """Parentheses, operators, and quotes should be removed."""
        result = build_prefix_tsquery("foo (bar) & baz")
        assert "(" not in result
        assert ")" not in result
        assert "foo:*" in result
        assert "baz:*" in result

    def test_short_words_filtered(self):
        """Words shorter than 2 characters should be filtered out."""
        assert build_prefix_tsquery("I a love") == "love:*"

    def test_empty_input_returns_empty(self):
        """Empty or whitespace-only input returns empty string."""
        assert build_prefix_tsquery("") == ""
        assert build_prefix_tsquery("   ") == ""

    def test_hyphens_split_into_separate_words(self):
        """Hyphenated words produce prefix matches for each part."""
        result = build_prefix_tsquery("well-known")
        assert "well:*" in result
        assert "known:*" in result


class TestSearch:
    """@brief Tests for SearchService.search()."""

    @pytest.fixture
    def mock_user(self):
        """@brief Create a mock User with id."""
        user = type("User", (), {"id": uuid.uuid4()})()
        return user

    @pytest.fixture
    def mock_repo(self):
        """@brief Create a mocked SearchRepository."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_repo):
        """@brief Build SearchService with mock repository."""
        return SearchService(search_repo=mock_repo, community_id=COMMUNITY_ID)

    @pytest.mark.asyncio
    async def test_returns_results_grouped_by_type(self, mock_user, mock_repo, service):
        """search should return results grouped by content type."""
        post = type(
            "Post",
            (),
            {
                "id": uuid.uuid4(),
                "content": "Test post content",
                "created_at": datetime.now(UTC),
            },
        )()
        user_result = type(
            "User",
            (),
            {
                "id": uuid.uuid4(),
                "display_name": "Alice",
                "username": "alice",
                "bio": "Developer",
                "created_at": datetime.now(UTC),
            },
        )()

        mock_repo.search_posts.return_value = ([(post, 0.5)], None, 1)
        mock_repo.search_users.return_value = ([(user_result, 0.3)], None, 1)
        mock_repo.search_events.return_value = ([], None, 0)

        result = await service.search(
            query="test",
            user=mock_user,
            content_types=["posts", "users", "events"],
            cursor=None,
            limit=20,
        )

        assert "posts" in result.results
        assert "users" in result.results
        assert "events" in result.results
        assert len(result.results["posts"].items) == 1
        assert len(result.results["users"].items) == 1
        assert len(result.results["events"].items) == 0

    @pytest.mark.asyncio
    async def test_filters_by_requested_content_types_only(self, mock_user, mock_repo, service):
        """search should only query requested content types."""
        mock_repo.search_posts.return_value = ([], None, 0)
        mock_repo.search_users.return_value = ([], None, 0)
        mock_repo.search_events.return_value = ([], None, 0)

        await service.search(
            query="foo",
            user=mock_user,
            content_types=["posts"],
            cursor=None,
            limit=10,
        )

        mock_repo.search_posts.assert_awaited_once()
        mock_repo.search_users.assert_not_awaited()
        mock_repo.search_events.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_passes_raw_query_and_prefix_to_repository(self, mock_user, mock_repo, service):
        """search should pass both raw query and prefix query to the repo."""
        mock_repo.search_posts.return_value = ([], None, 0)

        await service.search(
            query="hello world",
            user=mock_user,
            content_types=["posts"],
            cursor=None,
            limit=20,
        )

        call_args = mock_repo.search_posts.call_args
        assert call_args[0][0] == "hello world"
        assert call_args[0][1] == "hello:* & world:*"

    @pytest.mark.asyncio
    async def test_includes_comments_when_requested(self, mock_user, mock_repo, service):
        """search should query comments when 'comments' is in content_types."""
        comment = type(
            "Comment",
            (),
            {
                "id": uuid.uuid4(),
                "content": "Great post!",
                "post_id": uuid.uuid4(),
                "created_at": datetime.now(UTC),
            },
        )()
        mock_repo.search_comments.return_value = ([(comment, 0.4)], None, 1)
        mock_repo.search_posts.return_value = ([], None, 0)

        result = await service.search(
            query="great",
            user=mock_user,
            content_types=["posts", "comments"],
            cursor=None,
            limit=20,
        )

        mock_repo.search_comments.assert_awaited_once()
        assert "comments" in result.results
        assert len(result.results["comments"].items) == 1
        assert result.results["comments"].items[0].type == "comments"

    @pytest.mark.asyncio
    async def test_comment_result_includes_post_id(self, mock_user, mock_repo, service):
        """Comment search results should include the parent post_id."""
        post_id = uuid.uuid4()
        comment = type(
            "Comment",
            (),
            {
                "id": uuid.uuid4(),
                "content": "This is a great discussion",
                "post_id": post_id,
                "created_at": datetime.now(UTC),
            },
        )()
        mock_repo.search_comments.return_value = ([(comment, 0.6)], None, 1)

        result = await service.search(
            query="discussion",
            user=mock_user,
            content_types=["comments"],
            cursor=None,
            limit=20,
        )

        item = result.results["comments"].items[0]
        assert item.parent_id == post_id

    @pytest.mark.asyncio
    async def test_empty_query_returns_empty_results(self, mock_user, mock_repo, service):
        """search should return empty results for whitespace-only queries."""
        result = await service.search(
            query="   ",
            user=mock_user,
            content_types=["posts", "comments"],
            cursor=None,
            limit=20,
        )

        for type_result in result.results.values():
            assert len(type_result.items) == 0

    @pytest.mark.asyncio
    async def test_all_four_types_searched_concurrently(self, mock_user, mock_repo, service):
        """search should query all four types when all are requested."""
        mock_repo.search_posts.return_value = ([], None, 0)
        mock_repo.search_users.return_value = ([], None, 0)
        mock_repo.search_events.return_value = ([], None, 0)
        mock_repo.search_comments.return_value = ([], None, 0)

        await service.search(
            query="test",
            user=mock_user,
            content_types=["posts", "users", "events", "comments"],
            cursor=None,
            limit=20,
        )

        mock_repo.search_posts.assert_awaited_once()
        mock_repo.search_users.assert_awaited_once()
        mock_repo.search_events.assert_awaited_once()
        mock_repo.search_comments.assert_awaited_once()
