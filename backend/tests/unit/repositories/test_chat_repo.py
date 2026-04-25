"""
@file test_chat_repo.py
@brief Unit tests for ChatChannelRepository and ChatMessageRepository.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.chat import ChatMessage
from app.models.subgroup import ChatChannel
from app.repositories.chat_repo import (
    TOMBSTONE_CONTENT,
    ChatChannelRepository,
    ChatMessageRepository,
    decode_cursor,
    encode_cursor,
)

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _make_session() -> AsyncMock:
    """@brief Build an AsyncMock SQLAlchemy session."""
    session = AsyncMock()
    session.add = MagicMock()
    session.add_all = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    return session


class TestCursorEncoding:
    """@brief Round-trip tests for encode_cursor / decode_cursor."""

    def test_round_trip(self) -> None:
        """Cursor encode then decode reproduces the original tuple."""
        now = datetime.now(UTC)
        mid = uuid.uuid4()
        cursor = encode_cursor(now, mid)
        decoded = decode_cursor(cursor)
        assert decoded is not None
        ts, got_id = decoded
        assert ts.isoformat() == now.isoformat()
        assert got_id == mid

    def test_decode_invalid_returns_none(self) -> None:
        """decode_cursor tolerates garbage input."""
        assert decode_cursor("not-base64!") is None
        assert decode_cursor("") is None


class TestChatChannelRepositoryGetCommunityDefault:
    """@brief Tests for get_community_default()."""

    @pytest.mark.asyncio
    async def test_returns_channel_when_present(self) -> None:
        session = _make_session()
        ch = MagicMock(spec=ChatChannel)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = ch
        session.execute = AsyncMock(return_value=mock_result)

        repo = ChatChannelRepository(session)
        result = await repo.get_community_default(COMMUNITY_ID)

        assert result is ch
        session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_returns_none_when_missing(self) -> None:
        session = _make_session()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        repo = ChatChannelRepository(session)
        assert await repo.get_community_default(COMMUNITY_ID) is None


class TestChatChannelRepositoryGetOrCreateDm:
    """@brief Tests for get_or_create_dm()."""

    @pytest.mark.asyncio
    async def test_existing_dm_returned(self) -> None:
        """get_or_create_dm returns the existing channel without inserting."""
        session = _make_session()
        existing = MagicMock(spec=ChatChannel)
        existing.channel_type = "direct"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        session.execute = AsyncMock(return_value=mock_result)

        repo = ChatChannelRepository(session)
        channel, created = await repo.get_or_create_dm(uuid.uuid4(), uuid.uuid4(), COMMUNITY_ID)

        assert channel is existing
        assert created is False
        session.add.assert_not_called()
        session.add_all.assert_not_called()

    @pytest.mark.asyncio
    async def test_new_dm_created_with_two_participants(self) -> None:
        """get_or_create_dm inserts a channel plus two participant rows."""
        session = _make_session()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        repo = ChatChannelRepository(session)
        user_a = uuid.uuid4()
        user_b = uuid.uuid4()
        channel, created = await repo.get_or_create_dm(user_a, user_b, COMMUNITY_ID)

        assert created is True
        assert channel is not None
        session.add.assert_called_once()
        session.add_all.assert_called_once()
        call_args = session.add_all.call_args[0][0]
        assert len(call_args) == 2
        participant_users = {p.user_id for p in call_args}
        assert participant_users == {user_a, user_b}

    @pytest.mark.asyncio
    async def test_rejects_self_dm(self) -> None:
        """get_or_create_dm raises when both user ids are identical."""
        session = _make_session()
        repo = ChatChannelRepository(session)
        me = uuid.uuid4()
        with pytest.raises(ValueError):
            await repo.get_or_create_dm(me, me, COMMUNITY_ID)


class TestChatMessageRepositoryCreate:
    """@brief Tests for create_message()."""

    @pytest.mark.asyncio
    async def test_create_message_inserts_row(self) -> None:
        """create_message persists a ChatMessage with the provided fields."""
        session = _make_session()
        repo = ChatMessageRepository(session)
        channel_id = uuid.uuid4()
        author_id = uuid.uuid4()

        msg = await repo.create_message(
            community_id=COMMUNITY_ID,
            channel_id=channel_id,
            author_id=author_id,
            content="Hello",
        )

        session.add.assert_called_once()
        session.flush.assert_awaited()
        session.refresh.assert_awaited()
        assert isinstance(msg, ChatMessage)
        assert msg.community_id == COMMUNITY_ID
        assert msg.channel_id == channel_id
        assert msg.author_id == author_id
        assert msg.content == "Hello"


class TestChatMessageRepositorySoftDelete:
    """@brief Tests for soft_delete_message()."""

    @pytest.mark.asyncio
    async def test_soft_delete_writes_tombstone(self) -> None:
        """soft_delete_message replaces content with the tombstone marker."""
        session = _make_session()
        repo = ChatMessageRepository(session)
        msg = MagicMock(spec=ChatMessage)
        msg.content = "original"
        msg.edited_at = None

        updated = await repo.soft_delete_message(msg)

        assert updated.content == TOMBSTONE_CONTENT
        assert isinstance(updated.edited_at, datetime)
        session.flush.assert_awaited()
        session.refresh.assert_awaited_with(msg)


class TestChatMessageRepositoryHistoryPaginated:
    """@brief Tests for get_history_paginated()."""

    @pytest.mark.asyncio
    async def test_returns_rows_and_no_cursor_when_under_limit(self) -> None:
        """History returns (rows, None) when the page does not exceed limit."""
        session = _make_session()
        repo = ChatMessageRepository(session)
        rows = [(MagicMock(spec=ChatMessage, id=uuid.uuid4()), None) for _ in range(3)]
        for i, (m, _u) in enumerate(rows):
            m.created_at = datetime.now(UTC) - timedelta(seconds=i)
        mock_result = MagicMock()
        mock_result.all.return_value = rows
        session.execute = AsyncMock(return_value=mock_result)

        items, cursor = await repo.get_history_paginated(uuid.uuid4(), COMMUNITY_ID, limit=5)

        assert len(items) == 3
        assert cursor is None

    @pytest.mark.asyncio
    async def test_emits_cursor_when_over_limit(self) -> None:
        """History returns (rows[:limit], cursor) when there are more pages."""
        session = _make_session()
        repo = ChatMessageRepository(session)
        rows = []
        for i in range(6):
            m = MagicMock(spec=ChatMessage)
            m.id = uuid.uuid4()
            m.created_at = datetime.now(UTC) - timedelta(seconds=i)
            rows.append((m, None))
        mock_result = MagicMock()
        mock_result.all.return_value = rows
        session.execute = AsyncMock(return_value=mock_result)

        items, cursor = await repo.get_history_paginated(uuid.uuid4(), COMMUNITY_ID, limit=5)
        assert len(items) == 5
        assert cursor is not None
        decoded = decode_cursor(cursor)
        assert decoded is not None
