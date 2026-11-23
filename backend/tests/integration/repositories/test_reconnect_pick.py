"""
@file test_reconnect_pick.py
@brief Real-Postgres: reconnect ``pick`` chooses the stalest confirmed relative and
       skips recent contact, friends, snoozed, blocked and memorialized people;
       the daily run is idempotent and honours the community flag.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
import app.services.notifications.types  # noqa: F401
from app.models.chat import ChatMessage, DirectMessageParticipant
from app.models.community import Community
from app.models.moderation import UserBlock
from app.models.nudge import Nudge
from app.models.post import Comment, Post
from app.models.relation import Relation
from app.models.subgroup import ChatChannel
from app.models.user import User
from app.models.user_settings import UserSettings
from app.repositories.community_repo import CommunityRepository
from app.repositories.reconnect_repo import ReconnectRepository
from app.repositories.user_repo import UserRepository
from app.services.notification_service import NotificationService
from app.services.reconnect_service import ReconnectService

TEST_DB_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://nexara:nexara@localhost:5432/nexara_test"
)
CID = uuid.UUID("00000000-0000-0000-0000-000000000001")
NOW = datetime(2026, 11, 22, 15, 0, tzinfo=UTC)


def _ago(days: int) -> datetime:
    return NOW - timedelta(days=days)


@pytest.fixture
async def session():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        async with sess.begin():
            yield sess
            await sess.rollback()
    await engine.dispose()


async def _user(s: AsyncSession, name: str, **kw) -> User:
    sfx = uuid.uuid4().hex[:6]
    u = User(
        community_id=CID, email=f"rc_{name}_{sfx}@nexara.dev", username=f"rc_{name}_{sfx}",
        display_name=name, **kw,
    )  # fmt: skip
    s.add(u)
    await s.flush()
    return u


async def _rel(s: AsyncSession, a: User, b: User, kind="sibling", age=60, status="confirmed"):
    s.add(
        Relation(
            community_id=CID, from_user_id=a.id, to_user_id=b.id, kind=kind, status=status,
            created_by=a.id, created_at=_ago(age), confirmed_at=_ago(age),
        )
    )  # fmt: skip
    await s.flush()


async def _users(s: AsyncSession, *names: str) -> list[User]:
    return [await _user(s, n) for n in names]


def _svc(s: AsyncSession):
    notif = AsyncMock(spec=NotificationService)
    return (
        ReconnectService(
            ReconnectRepository(s), UserRepository(s), CommunityRepository(s), notif, CID
        ),
        notif,
    )


async def _dm(s: AsyncSession, a: User, b: User, days: int) -> None:
    ch = ChatChannel(community_id=CID, name="dm", channel_type="direct")
    s.add(ch)
    await s.flush()
    s.add_all([DirectMessageParticipant(channel_id=ch.id, user_id=u.id) for u in (a, b)])
    s.add(ChatMessage(community_id=CID, channel_id=ch.id, author_id=b.id, content="hi",
                      created_at=_ago(days)))  # fmt: skip
    await s.flush()


async def test_stalest_relative_picked(session: AsyncSession) -> None:
    me, old, older = await _users(session, "me", "old", "older")
    await _rel(session, me, old, age=60)
    await _rel(session, older, me, kind="parent", age=200)
    svc, _ = _svc(session)
    assert await svc.pick(me.id, NOW) == older.id


async def test_recent_dm_comment_or_kudos_excludes(session: AsyncSession) -> None:
    me, a, b, c = await _users(session, "me", "a", "b", "c")
    for other in (a, b, c):
        await _rel(session, me, other, age=100)
    await _dm(session, me, a, 10)
    post = Post(community_id=CID, author_id=b.id, content="x", visibility="community")
    session.add(post)
    await session.flush()
    session.add(Comment(community_id=CID, post_id=post.id, author_id=me.id, content="c",
                        created_at=_ago(5)))  # fmt: skip
    session.add(Post(community_id=CID, author_id=c.id, recipient_id=me.id, content="k",
                     visibility="community", created_at=_ago(3)))  # fmt: skip
    await session.flush()
    svc, _ = _svc(session)
    assert await svc.pick(me.id, NOW) is None


async def test_old_dm_still_stale(session: AsyncSession) -> None:
    me, a = await _user(session, "me"), await _user(session, "a")
    await _rel(session, me, a, age=300)
    await _dm(session, me, a, 45)
    svc, _ = _svc(session)
    assert await svc.pick(me.id, NOW) == a.id


async def test_friend_pending_new_and_inactive_never(session: AsyncSession) -> None:
    me, friend, pend, fresh, off, gone, blk = await _users(
        session, "me", "friend", "pend", "fresh", "off", "gone", "blk"
    )
    await _rel(session, me, friend, kind="friend", age=200)
    await _rel(session, me, pend, status="pending", age=200)
    await _rel(session, me, fresh, age=3)  # confirmed 3 days ago: not stale yet
    await _rel(session, me, off, age=200)
    await _rel(session, me, gone, age=200)
    await _rel(session, me, blk, age=200)
    off.is_active = False
    gone.memorialized_at = _ago(10)
    session.add(UserBlock(blocker_id=blk.id, blocked_id=me.id, community_id=CID))
    await session.flush()
    svc, _ = _svc(session)
    assert await svc.pick(me.id, NOW) is None


async def test_snooze_respected_until_expiry(session: AsyncSession) -> None:
    me, a = await _user(session, "me"), await _user(session, "a")
    await _rel(session, me, a, age=100)
    svc, _ = _svc(session)
    await svc.snooze(me.id, a.id, NOW)
    assert await svc.pick(me.id, NOW) is None
    assert await svc.pick(me.id, NOW + timedelta(days=91)) == a.id


async def test_recent_nudge_and_opt_out_yield_none(session: AsyncSession) -> None:
    me, a = await _user(session, "me"), await _user(session, "a")
    await _rel(session, me, a, age=100)
    svc, _ = _svc(session)
    session.add(Nudge(community_id=CID, sender_id=me.id, target_id=me.id,
                      nudge_type="reconnect", created_at=_ago(3)))  # fmt: skip
    await session.flush()
    assert await svc.pick(me.id, NOW) is None
    await session.execute(delete(Nudge).where(Nudge.target_id == me.id))
    assert await svc.pick(me.id, NOW) == a.id
    session.add(UserSettings(user_id=me.id, community_id=CID, reconnect_nudges=False))
    await session.flush()
    assert await svc.pick(me.id, NOW) is None


async def test_run_twice_sends_once_and_flag_off_skips(session: AsyncSession) -> None:
    me, a = await _user(session, "me"), await _user(session, "a")
    await _rel(session, me, a, age=100)
    svc, notif = _svc(session)
    community = await session.get(Community, CID)
    community.features = {"reconnect_nudges": False}
    await session.flush()
    await svc.run(NOW)
    assert [c for c in notif.notify.await_args_list if c.args[0] == me.id] == []
    community.features = {}
    await session.flush()
    await svc.run(NOW)
    await svc.run(NOW + timedelta(hours=1))
    mine = [c for c in notif.notify.await_args_list if c.args[0] == me.id]
    assert len(mine) == 1 and mine[0].args[1] == "reconnect"
    assert mine[0].args[2]["target_id"] == str(a.id)
