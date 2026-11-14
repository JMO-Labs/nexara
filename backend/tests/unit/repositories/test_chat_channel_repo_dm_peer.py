"""
@file test_chat_channel_repo_dm_peer.py
@brief Unit tests for ChatChannelRepository.get_dm_peer_id (nexara#384).
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.repositories.chat_channel_repo import ChatChannelRepository


@pytest.mark.parametrize("peer", [uuid.uuid4(), None])
async def test_get_dm_peer_id_returns_scalar(peer):
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = peer
    session.execute.return_value = result
    repo = ChatChannelRepository(session)

    got = await repo.get_dm_peer_id(uuid.uuid4(), uuid.uuid4())

    assert got == peer
    session.execute.assert_awaited_once()
