"""
@file test_mention_tags_service.py
@brief Unit tests for MentionTagsService.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.mention_tags import MentionTagsService

COMMUNITY_ID = uuid.uuid4()
ACTOR_ID = uuid.uuid4()
TARGET_ID = uuid.uuid4()


@pytest.fixture
def tag_repo():
    """@brief Mock TagRepository."""
    return AsyncMock()


@pytest.fixture
def service(tag_repo):
    """@brief MentionTagsService instance with mocked repo."""
    return MentionTagsService(tag_repo)


class TestSyncMentions:
    """@brief Tests for sync_mentions()."""

    @pytest.mark.asyncio
    async def test_sync_mentions_extracts_usernames(self, service, tag_repo):
        """sync_mentions() extracts @username mentions from content."""
        user1 = MagicMock(id=uuid.uuid4(), display_name="Alice")
        user2 = MagicMock(id=uuid.uuid4(), display_name="Bob")
        tag_repo.users_by_username.return_value = [user1, user2]
        tag_repo.blocked_with.return_value = set()
        tag_repo.replace_user_tags.return_value = []

        await service.sync_mentions(
            COMMUNITY_ID, "event", TARGET_ID, "@alice hello @bob", ACTOR_ID, "Editor"
        )

        tag_repo.users_by_username.assert_called_once_with(COMMUNITY_ID, ["alice", "bob"])

    @pytest.mark.asyncio
    async def test_sync_mentions_excludes_actor(self, service, tag_repo):
        """sync_mentions() never tags the actor."""
        actor_id = uuid.uuid4()
        other_user = MagicMock(id=uuid.uuid4(), display_name="Bob")
        tag_repo.users_by_username.return_value = [
            MagicMock(id=actor_id, display_name="Alice"),
            other_user,
        ]
        tag_repo.blocked_with.return_value = set()
        tag_repo.replace_user_tags.return_value = []

        await service.sync_mentions(
            COMMUNITY_ID, "event", TARGET_ID, "@alice @bob", actor_id, "Editor"
        )

        # Only "other_user" should be passed to replace_user_tags
        _, _, _, ids, _ = tag_repo.replace_user_tags.await_args.args
        assert len(ids) == 1
        assert ids[0] == other_user.id

    @pytest.mark.asyncio
    async def test_sync_mentions_filters_blocked_users(self, service, tag_repo):
        """sync_mentions() removes users in block relationships with the actor."""
        actor_id = uuid.uuid4()
        user1 = MagicMock(id=uuid.uuid4(), display_name="Alice")
        user2 = MagicMock(id=uuid.uuid4(), display_name="Bob")
        tag_repo.users_by_username.return_value = [user1, user2]
        tag_repo.blocked_with.return_value = {user1.id}  # user1 is blocked
        tag_repo.replace_user_tags.return_value = []

        await service.sync_mentions(
            COMMUNITY_ID, "event", TARGET_ID, "@alice @bob", actor_id, "Editor"
        )

        # Only user2 should pass through
        _, _, _, ids, _ = tag_repo.replace_user_tags.await_args.args
        assert len(ids) == 1
        assert ids[0] == user2.id

    @pytest.mark.asyncio
    async def test_sync_mentions_applies_visibility_filter(self, service, tag_repo):
        """sync_mentions() applies can_see predicate when provided."""
        actor_id = uuid.uuid4()
        user1 = MagicMock(id=uuid.uuid4(), display_name="Alice")
        user2 = MagicMock(id=uuid.uuid4(), display_name="Bob")
        tag_repo.users_by_username.return_value = [user1, user2]
        tag_repo.blocked_with.return_value = set()
        tag_repo.replace_user_tags.return_value = []

        # Only user2 can see the target
        async def can_see(uid):
            return uid == user2.id

        await service.sync_mentions(
            COMMUNITY_ID,
            "event",
            TARGET_ID,
            "@alice @bob",
            actor_id,
            "Editor",
            can_see=can_see,
        )

        _, _, _, ids, _ = tag_repo.replace_user_tags.await_args.args
        assert len(ids) == 1
        assert ids[0] == user2.id

    @pytest.mark.asyncio
    async def test_sync_mentions_notifies_new_tags_only(self, service, tag_repo):
        """sync_mentions() calls notify_callable for newly tagged users only."""
        actor_id = uuid.uuid4()
        user1 = MagicMock(id=uuid.uuid4(), display_name="Alice")
        user2 = MagicMock(id=uuid.uuid4(), display_name="Bob")
        tag_repo.users_by_username.return_value = [user1, user2]
        tag_repo.blocked_with.return_value = set()
        tag_repo.replace_user_tags.return_value = [user1.id]  # Only user1 is newly tagged

        notify_mock = AsyncMock()
        await service.sync_mentions(
            COMMUNITY_ID,
            "event",
            TARGET_ID,
            "@alice @bob",
            actor_id,
            "Editor",
            notify_callable=notify_mock,
            link="/app/events?event=123",
            label="an event",
        )

        # Only user1 should be notified
        assert notify_mock.await_count == 1
        call_args = notify_mock.await_args.args
        assert call_args[0] == user1.id
        assert call_args[1] == "mention"

    @pytest.mark.asyncio
    async def test_sync_mentions_returns_early_on_fresh_no_mentions(self, service, tag_repo):
        """sync_mentions() returns early when fresh=True and no mentions found."""
        await service.sync_mentions(
            COMMUNITY_ID, "event", TARGET_ID, "Hello world", uuid.uuid4(), "Editor", fresh=True
        )

        tag_repo.users_by_username.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_sync_mentions_syncs_on_update_no_mentions(self, service, tag_repo):
        """sync_mentions() with fresh=False syncs even with no mentions (clears tags)."""
        tag_repo.users_by_username.return_value = []
        tag_repo.replace_user_tags.return_value = []

        await service.sync_mentions(
            COMMUNITY_ID,
            "event",
            TARGET_ID,
            "Hello world",
            uuid.uuid4(),
            "Editor",
            fresh=False,
        )

        # Should call replace_user_tags even with no matches
        tag_repo.replace_user_tags.assert_called_once()
