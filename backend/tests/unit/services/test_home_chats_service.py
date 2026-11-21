"""
@file test_home_chats_service.py
@brief Unit tests for HomeChatsService ranking, limiting and shaping.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from app.models.chat import ChatMessage
from app.models.subgroup import ChatChannel
from app.models.user import User
from app.repositories.chat_channel_repo import ChatChannelRepository
from app.repositories.chat_read_repo import ChannelStat, ChatReadRepository
from app.services.home_chats_service import HomeChatsService

COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
NOW = datetime(2026, 11, 19, 12, 0, tzinfo=UTC)


def _channel(name: str, ctype: str = "community") -> MagicMock:
    c = MagicMock(spec=ChatChannel)
    c.id = uuid.uuid4()
    c.name = name
    c.channel_type = ctype
    c.subgroup_id = uuid.uuid4() if ctype == "subgroup" else None
    c.created_at = NOW - timedelta(days=30)
    return c


def _msg(age_min: int, content: str = "hello") -> MagicMock:
    m = MagicMock(spec=ChatMessage)
    m.id = uuid.uuid4()
    m.content = content
    m.created_at = NOW - timedelta(minutes=age_min)
    return m


def _stat(age_min: int, unread: int = 0, mention: bool = False, content: str = "hello"):
    return ChannelStat(_msg(age_min, content), "Ana", unread, mention)


def _user() -> MagicMock:
    u = MagicMock(spec=User)
    u.id = uuid.uuid4()
    u.username = "me"
    return u


def _svc(channels, stats, dms=None):
    repo = AsyncMock(spec=ChatChannelRepository)
    repo.list_for_user.return_value = channels
    repo.list_dm_threads.return_value = dms or []
    reads = AsyncMock(spec=ChatReadRepository)
    reads.channel_stats.return_value = stats
    return HomeChatsService(repo, reads, COMMUNITY_ID)


async def test_ranks_mentions_then_unread_then_recent():
    recent, unread, mention = _channel("recent"), _channel("unread"), _channel("mention")
    stats = {
        recent.id: _stat(1),
        unread.id: _stat(60, unread=2),
        mention.id: _stat(600, unread=1, mention=True),
    }
    resp = await _svc([recent, unread, mention], stats).list(_user(), 4)
    assert [t.name for t in resp.items] == ["mention", "unread", "recent"]


async def test_limit_applies_after_ranking():
    chans = [_channel(f"c{i}") for i in range(3)]
    stats = {c.id: _stat(i + 1) for i, c in enumerate(chans)}
    stats[chans[2].id] = _stat(5, unread=1)
    resp = await _svc(chans, stats).list(_user(), 2)
    assert len(resp.items) == 2
    assert resp.items[0].name == "c2"


async def test_dm_uses_peer_name():
    dm = _channel("dm-xyz", "direct")
    peer = MagicMock(spec=User)
    peer.id = uuid.uuid4()
    peer.display_name = "Leo Delgado"
    peer.avatar_url = None
    resp = await _svc([dm], {dm.id: _stat(1)}, [(dm, peer)]).list(_user(), 4)
    assert resp.items[0].name == "Leo Delgado"
    assert resp.items[0].peer.id == peer.id


async def test_truncates_preview():
    c = _channel("c")
    resp = await _svc([c], {c.id: _stat(1, content="x" * 300)}).list(_user(), 4)
    content = resp.items[0].last_message.content
    assert len(content) <= 140
    assert content.endswith("…")


async def test_channel_without_messages_uses_channel_created_at():
    c = _channel("empty")
    stats = {c.id: ChannelStat(None, None, 0, False)}
    resp = await _svc([c], stats).list(_user(), 4)
    assert resp.items[0].last_message is None
    assert resp.items[0].last_activity_at == c.created_at
