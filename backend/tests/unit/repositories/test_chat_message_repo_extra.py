"""
@file test_chat_message_repo_extra.py
@brief Coverage tests for ChatMessageRepository get/cursor/block/edit paths.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.chat import ChatMessage
from app.repositories.chat_message_repo import (
    TOMBSTONE_CONTENT,
    ChatMessageRepository,
    encode_cursor,
)

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _session(result: MagicMock) -> AsyncMock:
    """@brief AsyncMock session returning ``result`` from execute."""
    session = AsyncMock()
    session.add = MagicMock()
    session.execute = AsyncMock(return_value=result)
    return session


def _sql(session: AsyncMock) -> str:
    """@brief Compiled SQL of the last executed statement."""
    return str(session.execute.call_args[0][0])


class TestGet:
    """@brief get()."""

    async def test_returns_scalar(self) -> None:
        """get returns the row from scalar_one_or_none."""
        msg = MagicMock(spec=ChatMessage)
        res = MagicMock()
        res.scalar_one_or_none.return_value = msg
        session = _session(res)
        got = await ChatMessageRepository(session).get(uuid.uuid4(), COMMUNITY_ID)
        assert got is msg
        assert "community_id" in _sql(session)


class TestHistoryCursorAndBlock:
    """@brief get_history_paginated cursor and viewer filter."""

    async def test_valid_cursor_adds_where(self) -> None:
        """A decodable cursor adds a created_at comparison."""
        res = MagicMock()
        res.all.return_value = []
        session = _session(res)
        cursor = encode_cursor(datetime.now(UTC), uuid.uuid4())
        await ChatMessageRepository(session).get_history_paginated(
            uuid.uuid4(), COMMUNITY_ID, cursor=cursor
        )
        assert "created_at <" in _sql(session)

    async def test_invalid_cursor_ignored(self) -> None:
        """An undecodable cursor is ignored."""
        res = MagicMock()
        res.all.return_value = []
        session = _session(res)
        await ChatMessageRepository(session).get_history_paginated(
            uuid.uuid4(), COMMUNITY_ID, cursor="garbage!"
        )
        assert "created_at <" not in _sql(session)

    async def test_viewer_applies_block_filter(self) -> None:
        """viewer_id routes the statement through apply_block_filter."""
        res = MagicMock()
        res.all.return_value = []
        session = _session(res)
        repo = ChatMessageRepository(session)
        repo.apply_block_filter = MagicMock(side_effect=lambda s, v: s)  # type: ignore[method-assign]
        viewer = uuid.uuid4()
        await repo.get_history_paginated(uuid.uuid4(), COMMUNITY_ID, viewer_id=viewer)
        repo.apply_block_filter.assert_called_once()
        assert repo.apply_block_filter.call_args[0][1] == viewer


class TestListWithBlockFilter:
    """@brief list_with_block_filter()."""

    async def test_returns_scalars_and_filters(self) -> None:
        """Returns a list of messages after applying block filter."""
        msgs = [MagicMock(spec=ChatMessage), MagicMock(spec=ChatMessage)]
        res = MagicMock()
        res.scalars.return_value.all.return_value = msgs
        session = _session(res)
        repo = ChatMessageRepository(session)
        repo.apply_block_filter = MagicMock(side_effect=lambda s, v: s)  # type: ignore[method-assign]
        out = await repo.list_with_block_filter(
            uuid.uuid4(), COMMUNITY_ID, uuid.uuid4(), limit=2
        )
        assert out == msgs
        repo.apply_block_filter.assert_called_once()


class TestUpdateAndTombstone:
    """@brief update_content() and is_tombstone()."""

    async def test_update_content_stamps_edited_at(self) -> None:
        """update_content sets content/edited_at and flushes."""
        session = AsyncMock()
        msg = MagicMock(spec=ChatMessage)
        msg.edited_at = None
        out = await ChatMessageRepository(session).update_content(msg, "new")
        assert out.content == "new"
        assert isinstance(out.edited_at, datetime)
        session.flush.assert_awaited()
        session.refresh.assert_awaited_with(msg)

    def test_is_tombstone_dict_and_model(self) -> None:
        """is_tombstone handles dicts and models."""
        assert ChatMessageRepository.is_tombstone({"content": TOMBSTONE_CONTENT})
        assert not ChatMessageRepository.is_tombstone({"content": "hi"})
        m = MagicMock(spec=ChatMessage)
        m.content = TOMBSTONE_CONTENT
        assert ChatMessageRepository.is_tombstone(m)
        m.content = "x"
        assert not ChatMessageRepository.is_tombstone(m)
