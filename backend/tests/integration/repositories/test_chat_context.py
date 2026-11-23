"""
@file test_chat_context.py
@brief Real-Postgres privacy rules for the chat details-panel context.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401 — registers all mapped classes
from app.core.exceptions import NotFoundError
from app.models.chat import DirectMessageParticipant
from app.models.community import Community
from app.models.event import Event, EventAttendance
from app.models.subgroup import ChatChannel, Subgroup, SubgroupMember
from app.models.user import User
from app.models.user_settings import UserSettings
from app.repositories.chat_channel_repo import ChatChannelRepository
from app.repositories.chat_context_repo import ChatContextRepository
from app.services.chat_context_service import ChatContextService

TEST_DB_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://nexara:nexara@localhost:5432/nexara_test"
)


@pytest.fixture
async def session():
    """@brief Transactional session rolled back after each test."""
    engine = create_async_engine(TEST_DB_URL, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        async with sess.begin():
            yield sess
            await sess.rollback()
    await engine.dispose()


async def _user(s: AsyncSession, cid: uuid.UUID, **kw) -> User:
    tag = uuid.uuid4().hex[:8]
    u = User(
        community_id=cid, email=f"c_{tag}@x.dev", username=f"c_{tag}", display_name=f"U{tag}", **kw
    )
    s.add(u)
    await s.flush()
    return u


async def _dm(s: AsyncSession, cid: uuid.UUID, a: User, b: User) -> ChatChannel:
    ch = ChatChannel(community_id=cid, name="dm", channel_type="direct")
    s.add(ch)
    await s.flush()
    s.add_all([DirectMessageParticipant(channel_id=ch.id, user_id=u.id) for u in (a, b)])
    await s.flush()
    return ch


def _svc(s: AsyncSession, cid: uuid.UUID) -> ChatContextService:
    return ChatContextService(ChatChannelRepository(s), ChatContextRepository(s), cid)


async def _event(s, cid, author, title, visibility, subgroup_id=None) -> Event:
    start = datetime.now(UTC) + timedelta(days=2)
    e = Event(
        community_id=cid,
        author_id=author.id,
        title=title,
        starts_at=start,
        ends_at=start + timedelta(hours=1),
        visibility=visibility,
        subgroup_id=subgroup_id,
        ical_uid=uuid.uuid4().hex,
    )
    s.add(e)
    await s.flush()
    return e


async def test_non_participant_gets_404(session: AsyncSession) -> None:
    c = Community(name=f"cc-{uuid.uuid4().hex[:6]}")
    session.add(c)
    await session.flush()
    a, b, outsider = [await _user(session, c.id) for _ in range(3)]
    ch = await _dm(session, c.id, a, b)
    with pytest.raises(NotFoundError):
        await _svc(session, c.id).get_context(outsider, ch.id)


async def test_peer_privacy_gates(session: AsyncSession) -> None:
    c = Community(name=f"cc-{uuid.uuid4().hex[:6]}")
    session.add(c)
    await session.flush()
    me = await _user(session, c.id)
    peer = await _user(
        session,
        c.id,
        birthday=date(1990, 1, 1),
        timezone="Europe/Paris",
        last_seen_at=datetime.now(UTC),
    )
    session.add(
        UserSettings(
            user_id=peer.id,
            community_id=c.id,
            show_last_seen=False,
            show_birthday_to="nobody",
        )
    )
    await session.flush()
    ch = await _dm(session, c.id, me, peer)
    res = await _svc(session, c.id).get_context(me, ch.id)
    assert res.kind == "dm"
    assert res.peer.last_seen_at is None
    assert res.peer.birthday_in_days is None
    assert res.peer.local_time_tz == "Europe/Paris"


async def test_shared_event_visibility_and_blocked_minimal(session: AsyncSession) -> None:
    c = Community(name=f"cc-{uuid.uuid4().hex[:6]}")
    session.add(c)
    await session.flush()
    me, peer, other = [await _user(session, c.id) for _ in range(3)]
    sg = Subgroup(community_id=c.id, name="Secret", slug=f"s-{uuid.uuid4().hex[:8]}")
    session.add(sg)
    await session.flush()
    session.add(SubgroupMember(subgroup_id=sg.id, user_id=peer.id))
    session.add(SubgroupMember(subgroup_id=sg.id, user_id=other.id))
    ok = await _event(session, c.id, peer, "Picnic", "community")
    hidden = await _event(session, c.id, other, "Hidden", "subgroup", sg.id)
    for ev in (ok, hidden):
        for u in (me, peer):
            session.add(EventAttendance(community_id=c.id, event_id=ev.id, user_id=u.id))
    await session.flush()
    ch = await _dm(session, c.id, me, peer)
    res = await _svc(session, c.id).get_context(me, ch.id)
    assert [e.title for e in res.upcoming_events] == ["Picnic"]
    assert res.shared_groups == []

    from app.models.moderation import UserBlock

    session.add(UserBlock(community_id=c.id, blocker_id=me.id, blocked_id=peer.id))
    await session.flush()
    res = await _svc(session, c.id).get_context(me, ch.id)
    assert res.upcoming_events == [] and res.peer.avatar_url is None
    assert res.peer.last_seen_at is None
