"""
@file test_chat_service.py
@brief Unit tests for ChatService.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import AuthorizationError, NotFoundError, RateLimitError
from app.models.chat import ChatMessage
from app.models.subgroup import ChatChannel
from app.models.user import User
from app.repositories.chat_repo import (
    TOMBSTONE_CONTENT,
    ChatChannelRepository,
    ChatMessageRepository,
)
from app.services.chat_service import (
    CHAT_RATE_LIMIT_PER_MINUTE,
    ChatService,
    channel_pubsub_name,
    serialize_message,
)

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
USER_ID = uuid.uuid4()
OTHER_USER_ID = uuid.uuid4()
ADMIN_ID = uuid.uuid4()
CHANNEL_ID = uuid.uuid4()
MESSAGE_ID = uuid.uuid4()


def _make_user(user_id: uuid.UUID = USER_ID, role: str = "member") -> User:
    """@brief Create a mock User instance."""
    u = MagicMock(spec=User)
    u.id = user_id
    u.username = "alice"
    u.display_name = "Alice"
    u.avatar_url = None
    u.role = role
    return u


def _make_channel(channel_type: str = "community") -> ChatChannel:
    """@brief Create a mock ChatChannel."""
    c = MagicMock(spec=ChatChannel)
    c.id = CHANNEL_ID
    c.community_id = COMMUNITY_ID
    c.channel_type = channel_type
    c.subgroup_id = None
    c.name = "general"
    c.created_at = datetime.now(UTC)
    return c


def _make_message(
    author_id: uuid.UUID | None = USER_ID,
    content: str = "hello",
) -> ChatMessage:
    """@brief Create a mock ChatMessage."""
    m = MagicMock(spec=ChatMessage)
    m.id = MESSAGE_ID
    m.community_id = COMMUNITY_ID
    m.channel_id = CHANNEL_ID
    m.author_id = author_id
    m.content = content
    m.created_at = datetime.now(UTC)
    m.edited_at = None
    return m


@pytest.fixture
def channel_repo() -> AsyncMock:
    """@brief Mock ChatChannelRepository."""
    return AsyncMock(spec=ChatChannelRepository)


@pytest.fixture
def message_repo() -> AsyncMock:
    """@brief Mock ChatMessageRepository."""
    return AsyncMock(spec=ChatMessageRepository)


@pytest.fixture
def broadcaster() -> AsyncMock:
    """@brief Mock pub/sub broadcaster (async callable)."""
    mock = AsyncMock(return_value=1)
    return mock


@pytest.fixture
def link_preview_enqueue() -> MagicMock:
    """@brief Mock Celery task enqueue (sync call)."""
    return MagicMock()


@pytest.fixture
def service(channel_repo, message_repo, broadcaster, link_preview_enqueue) -> ChatService:
    """@brief ChatService with mocked collaborators (no rate limiter)."""
    return ChatService(
        channel_repo=channel_repo,
        message_repo=message_repo,
        community_id=COMMUNITY_ID,
        broadcaster=broadcaster,
        link_preview_enqueue=link_preview_enqueue,
    )


class TestSerializeMessage:
    """@brief Tests for the standalone serializer."""

    def test_serialize_includes_deleted_flag(self) -> None:
        """serialize_message reports deleted=True for tombstones."""
        msg = _make_message(content=TOMBSTONE_CONTENT)
        data = serialize_message(msg, _make_user())
        assert data["deleted"] is True
        assert data["content"] == TOMBSTONE_CONTENT

    def test_serialize_without_author(self) -> None:
        """serialize_message handles author=None gracefully."""
        msg = _make_message()
        data = serialize_message(msg, None)
        assert data["author"] is None


class TestSendMessage:
    """@brief Tests for send_message()."""

    @pytest.mark.asyncio
    async def test_send_message_persists_and_broadcasts(
        self, service, channel_repo, message_repo, broadcaster
    ) -> None:
        """send_message persists + publishes + returns wire payload."""
        user = _make_user()
        channel = _make_channel()
        channel_repo.get_for_user.return_value = channel
        message_repo.create_message.return_value = _make_message()

        result = await service.send_message(user, CHANNEL_ID, "hi world")

        channel_repo.get_for_user.assert_awaited_once_with(CHANNEL_ID, user.id, COMMUNITY_ID)
        message_repo.create_message.assert_awaited_once()
        kwargs = message_repo.create_message.call_args.kwargs
        assert kwargs["community_id"] == COMMUNITY_ID
        assert kwargs["channel_id"] == CHANNEL_ID
        assert kwargs["author_id"] == user.id
        assert kwargs["content"] == "hi world"

        broadcaster.assert_awaited_once()
        call_args = broadcaster.call_args[0]
        assert call_args[0] == channel_pubsub_name(CHANNEL_ID)
        envelope = call_args[1]
        assert envelope["type"] == "chat.message"
        assert envelope["payload"]["content"] == "hello"

        assert result["channel_id"] == str(CHANNEL_ID)

    @pytest.mark.asyncio
    async def test_send_message_raises_when_channel_missing(self, service, channel_repo) -> None:
        """send_message raises NotFoundError when channel is inaccessible."""
        channel_repo.get_for_user.return_value = None
        with pytest.raises(NotFoundError):
            await service.send_message(_make_user(), CHANNEL_ID, "hi")

    @pytest.mark.asyncio
    async def test_send_message_enqueues_link_preview_task(
        self, service, channel_repo, message_repo, link_preview_enqueue
    ) -> None:
        """send_message dispatches a Celery task for each URL in the content."""
        channel_repo.get_for_user.return_value = _make_channel()
        message_repo.create_message.return_value = _make_message()

        await service.send_message(
            _make_user(),
            CHANNEL_ID,
            "check https://example.com and https://example.org",
        )

        assert link_preview_enqueue.call_count == 2
        for call in link_preview_enqueue.call_args_list:
            assert call.kwargs.get("message_id") == str(MESSAGE_ID)

    @pytest.mark.asyncio
    async def test_send_message_rate_limit_blocks(
        self, channel_repo, message_repo, broadcaster, link_preview_enqueue
    ) -> None:
        """send_message raises RateLimitError after the per-minute quota."""
        rate_limiter = AsyncMock()
        rate_limiter.incr = AsyncMock(return_value=CHAT_RATE_LIMIT_PER_MINUTE + 1)
        rate_limiter.expire = AsyncMock()

        svc = ChatService(
            channel_repo=channel_repo,
            message_repo=message_repo,
            community_id=COMMUNITY_ID,
            rate_limiter=rate_limiter,
            broadcaster=broadcaster,
            link_preview_enqueue=link_preview_enqueue,
        )
        with pytest.raises(RateLimitError):
            await svc.send_message(_make_user(), CHANNEL_ID, "hi")

    @pytest.mark.asyncio
    async def test_send_message_rate_limit_allows_under_threshold(
        self, channel_repo, message_repo, broadcaster, link_preview_enqueue
    ) -> None:
        """send_message succeeds when the user is under the quota."""
        rate_limiter = AsyncMock()
        rate_limiter.incr = AsyncMock(return_value=1)
        rate_limiter.expire = AsyncMock()
        channel_repo.get_for_user.return_value = _make_channel()
        message_repo.create_message.return_value = _make_message()

        svc = ChatService(
            channel_repo=channel_repo,
            message_repo=message_repo,
            community_id=COMMUNITY_ID,
            rate_limiter=rate_limiter,
            broadcaster=broadcaster,
            link_preview_enqueue=link_preview_enqueue,
        )
        await svc.send_message(_make_user(), CHANNEL_ID, "hi")
        rate_limiter.incr.assert_awaited_once()
        rate_limiter.expire.assert_awaited_once()


class TestEditMessage:
    """@brief Tests for edit_message()."""

    @pytest.mark.asyncio
    async def test_edit_by_author(self, service, message_repo, broadcaster) -> None:
        """edit_message lets the author mutate content and broadcasts update."""
        user = _make_user()
        existing = _make_message(author_id=user.id, content="original")
        message_repo.get.return_value = existing

        async def fake_update(msg, new):
            msg.content = new
            msg.edited_at = datetime.now(UTC)
            return msg

        message_repo.update_content.side_effect = fake_update

        result = await service.edit_message(user, MESSAGE_ID, "updated")

        assert result["content"] == "updated"
        broadcaster.assert_awaited_once()
        envelope = broadcaster.call_args[0][1]
        assert envelope["type"] == "chat.updated"

    @pytest.mark.asyncio
    async def test_edit_by_non_author_rejected(self, service, message_repo) -> None:
        """edit_message refuses non-author callers."""
        user = _make_user(user_id=USER_ID)
        existing = _make_message(author_id=OTHER_USER_ID)
        message_repo.get.return_value = existing
        with pytest.raises(AuthorizationError):
            await service.edit_message(user, MESSAGE_ID, "nope")

    @pytest.mark.asyncio
    async def test_edit_missing_message(self, service, message_repo) -> None:
        """edit_message raises NotFoundError when the message is gone."""
        message_repo.get.return_value = None
        with pytest.raises(NotFoundError):
            await service.edit_message(_make_user(), MESSAGE_ID, "x")

    @pytest.mark.asyncio
    async def test_edit_rejected_on_tombstone(self, service, message_repo) -> None:
        """edit_message refuses previously soft-deleted messages."""
        user = _make_user()
        existing = _make_message(author_id=user.id, content=TOMBSTONE_CONTENT)
        message_repo.get.return_value = existing
        with pytest.raises(NotFoundError):
            await service.edit_message(user, MESSAGE_ID, "x")


class TestDeleteMessage:
    """@brief Tests for delete_message()."""

    @pytest.mark.asyncio
    async def test_delete_by_author(self, service, message_repo, broadcaster) -> None:
        """Author can delete their own message, broadcasts chat.deleted."""
        user = _make_user()
        existing = _make_message(author_id=user.id)
        message_repo.get.return_value = existing

        async def fake_delete(msg):
            msg.content = TOMBSTONE_CONTENT
            msg.edited_at = datetime.now(UTC)
            return msg

        message_repo.soft_delete_message.side_effect = fake_delete

        await service.delete_message(user, MESSAGE_ID)
        broadcaster.assert_awaited_once()
        envelope = broadcaster.call_args[0][1]
        assert envelope["type"] == "chat.deleted"
        assert envelope["payload"]["deleted"] is True

    @pytest.mark.asyncio
    async def test_delete_by_admin(self, service, message_repo, broadcaster) -> None:
        """Admin can delete anybody's message."""
        admin = _make_user(user_id=ADMIN_ID, role="admin")
        existing = _make_message(author_id=OTHER_USER_ID)
        message_repo.get.return_value = existing

        async def fake_delete(msg):
            msg.content = TOMBSTONE_CONTENT
            msg.edited_at = datetime.now(UTC)
            return msg

        message_repo.soft_delete_message.side_effect = fake_delete

        await service.delete_message(admin, MESSAGE_ID)
        message_repo.soft_delete_message.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_unauthorized(self, service, message_repo) -> None:
        """Regular non-author caller cannot delete."""
        user = _make_user(user_id=USER_ID)
        existing = _make_message(author_id=OTHER_USER_ID)
        message_repo.get.return_value = existing
        with pytest.raises(AuthorizationError):
            await service.delete_message(user, MESSAGE_ID)

    @pytest.mark.asyncio
    async def test_delete_missing_message(self, service, message_repo) -> None:
        """delete_message raises NotFoundError for missing messages."""
        message_repo.get.return_value = None
        with pytest.raises(NotFoundError):
            await service.delete_message(_make_user(), MESSAGE_ID)


class TestDMCreation:
    """@brief Tests for create_or_get_dm()."""

    @pytest.mark.asyncio
    async def test_creates_or_fetches(self, service, channel_repo) -> None:
        """create_or_get_dm delegates to the repo and returns the channel."""
        user = _make_user()
        peer = uuid.uuid4()
        channel = _make_channel(channel_type="direct")
        channel_repo.get_or_create_dm.return_value = (channel, True)

        result = await service.create_or_get_dm(user, peer)

        channel_repo.get_or_create_dm.assert_awaited_once_with(user.id, peer, COMMUNITY_ID)
        assert result is channel

    @pytest.mark.asyncio
    async def test_rejects_self_dm(self, service) -> None:
        """create_or_get_dm rejects DMing yourself."""
        user = _make_user()
        with pytest.raises(AuthorizationError):
            await service.create_or_get_dm(user, user.id)


class TestGetHistory:
    """@brief Tests for get_history()."""

    @pytest.mark.asyncio
    async def test_returns_paginated_items(self, service, channel_repo, message_repo) -> None:
        """get_history serialises rows and surfaces the cursor."""
        user = _make_user()
        channel_repo.get_for_user.return_value = _make_channel()
        msg = _make_message()
        message_repo.get_history_paginated.return_value = ([(msg, user)], "cursor-xyz")

        result = await service.get_history(user, CHANNEL_ID, cursor=None, limit=10)

        assert result["has_more"] is True
        assert result["cursor"] == "cursor-xyz"
        assert len(result["items"]) == 1
        assert result["items"][0]["id"] == str(MESSAGE_ID)

    @pytest.mark.asyncio
    async def test_raises_when_channel_missing(self, service, channel_repo) -> None:
        """get_history raises NotFoundError when channel is inaccessible."""
        channel_repo.get_for_user.return_value = None
        with pytest.raises(NotFoundError):
            await service.get_history(_make_user(), CHANNEL_ID)
