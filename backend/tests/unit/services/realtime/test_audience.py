"""
@file test_audience.py
@brief Unit tests for realtime audience resolution and emission.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.realtime.audience import emit_to_audience, resolve_audience
from app.services.realtime.events import EventType, UserTarget

CID = uuid.uuid4()
SG = uuid.uuid4()
AUTHOR = uuid.uuid4()
MEMBER = uuid.uuid4()
BLOCKER = uuid.uuid4()
BLOCKED = uuid.uuid4()


def _session(*results: list[uuid.UUID]) -> AsyncMock:
    """@brief Session whose successive execute() calls return the given id lists."""
    session = AsyncMock()
    outs = []
    for ids in results:
        r = MagicMock()
        r.scalars.return_value.all.return_value = ids
        outs.append(r)
    session.execute.side_effect = outs
    return session


class TestResolveAudience:
    @pytest.mark.asyncio
    async def test_private_is_author_only(self):
        session = _session()
        got = await resolve_audience(
            session, CID, visibility="private", subgroup_id=None, author_id=AUTHOR
        )
        assert got == [AUTHOR]
        session.execute.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_subgroup_members_only_plus_author(self):
        session = _session([MEMBER], [])
        got = await resolve_audience(
            session, CID, visibility="subgroup", subgroup_id=SG, author_id=AUTHOR
        )
        assert set(got) == {MEMBER, AUTHOR}

    @pytest.mark.asyncio
    async def test_community_all_members(self):
        other = uuid.uuid4()
        session = _session([MEMBER, other], [])
        got = await resolve_audience(
            session, CID, visibility="community", subgroup_id=None, author_id=AUTHOR
        )
        assert set(got) == {MEMBER, other, AUTHOR}

    @pytest.mark.asyncio
    async def test_blocks_either_direction_excluded(self):
        session = _session([MEMBER, BLOCKER, BLOCKED], [BLOCKER, BLOCKED])
        got = await resolve_audience(
            session, CID, visibility="community", subgroup_id=None, author_id=AUTHOR
        )
        assert set(got) == {MEMBER, AUTHOR}

    @pytest.mark.asyncio
    async def test_subgroup_without_id_is_author_only(self):
        session = _session()
        got = await resolve_audience(
            session, CID, visibility="subgroup", subgroup_id=None, author_id=AUTHOR
        )
        assert got == [AUTHOR]


class TestEmitToAudience:
    @pytest.mark.asyncio
    async def test_one_event_per_user(self):
        bus = AsyncMock()
        await emit_to_audience(bus, [AUTHOR, MEMBER], EventType.FEED_UPDATE, {"a": 1})
        events = [c.args[0] for c in bus.emit.await_args_list]
        assert len(events) == 2
        assert all(isinstance(e.target, UserTarget) for e in events)
        assert {e.target.user_id for e in events} == {AUTHOR, MEMBER}
        assert all(e.payload == {"a": 1} and e.type == EventType.FEED_UPDATE for e in events)
