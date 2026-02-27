"""
@file test_search_service.py
@brief Unit tests for SearchService.

Tests to_safe_tsquery sanitization and search() aggregation
using mocked SearchRepository.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.services.search_service import SearchService

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


class TestToSafeTsquery:
    """@brief Tests for SearchService.to_safe_tsquery()."""

    def test_handles_single_word(self):
        """to_safe_tsquery should return a single word unchanged."""
        assert SearchService.to_safe_tsquery("word") == "word"

    def test_joins_multiple_words_with_and(self):
        """to_safe_tsquery should join multiple words with &."""
        assert SearchService.to_safe_tsquery("word1 word2") == "word1 & word2"

    def test_handles_quoted_phrases(self):
        """to_safe_tsquery should convert quoted phrases to proximity with <->."""
        result = SearchService.to_safe_tsquery('"hello world"')
        assert "hello" in result and "world" in result
        assert "<->" in result

    def test_strips_sql_special_characters(self):
        """to_safe_tsquery should strip parentheses, &, |, !, : and similar."""
        result = SearchService.to_safe_tsquery("foo (bar) & | ! : baz")
        assert "(" not in result and ")" not in result
        assert "foo" in result or "bar" in result or "baz" in result


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

    @pytest.mark.asyncio
    async def test_returns_results_grouped_by_type(self, mock_user, mock_repo):
        """search should return results grouped by content type."""
        post = type("Post", (), {
            "id": uuid.uuid4(),
            "content": "Test post content",
            "created_at": datetime.now(timezone.utc),
        })()
        user_result = type("User", (), {
            "id": uuid.uuid4(),
            "display_name": "Alice",
            "username": "alice",
            "bio": "Developer",
            "created_at": datetime.now(timezone.utc),
        })()

        mock_repo.search_posts.return_value = ([(post, 0.5)], None, 1)
        mock_repo.search_users.return_value = ([(user_result, 0.3)], None, 1)
        mock_repo.search_events.return_value = ([], None, 0)

        service = SearchService(search_repo=mock_repo, community_id=COMMUNITY_ID)
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
    async def test_filters_by_requested_content_types_only(self, mock_user, mock_repo):
        """search should only query requested content types."""
        mock_repo.search_posts.return_value = ([], None, 0)
        mock_repo.search_users.return_value = ([], None, 0)
        mock_repo.search_events.return_value = ([], None, 0)

        service = SearchService(search_repo=mock_repo, community_id=COMMUNITY_ID)
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
