"""
@file test_story_flow.py
@brief Real-Postgres tests: StoryService + StoryRepository rules (silent
       decline, block/memorial refusal, party-only access, reminder once,
       expiry, answer linking, Stories-tab visibility).
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.core.exceptions import AppError, NotFoundError
from app.models.community import Community
from app.models.media import Media
from app.models.moderation import UserBlock
from app.models.post import Post, PostMedia
from app.models.user import User
from app.repositories.community_repo import CommunityRepository
from app.repositories.story_repo import StoryRepository
from app.services.story_service import StoryService

TEST_DB_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://nexara:nexara@localhost:5432/nexara_test"
)
CID = uuid.UUID("00000000-0000-0000-0000-000000000001")


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


async def _user(s: AsyncSession, **kw) -> User:
    tag = uuid.uuid4().hex[:8]
    u = User(community_id=CID, email=f"st_{tag}@nexara.dev", username=f"st_{tag}",
             display_name=f"Name {tag}", **kw)  # fmt: skip
    s.add(u)
    await s.flush()
    return u


async def _post(s: AsyncSession, author: User, text="hi", audio=False, visibility="community"):
    p = Post(community_id=CID, author_id=author.id, content=text, visibility=visibility)
    s.add(p)
    await s.flush()
    if audio:
        m = Media(community_id=CID, uploader_id=author.id, filename="a.m4a",
                  content_type="audio/mp4", storage_key=f"k/{uuid.uuid4()}", size_bytes=1,
                  status="ready")  # fmt: skip
        s.add(m)
        await s.flush()
        s.add(PostMedia(post_id=p.id, media_id=m.id, position=0))
        await s.flush()
    return p


def _svc(s: AsyncSession) -> tuple[StoryService, AsyncMock]:
    notify = AsyncMock()
    comm = MagicMock(spec=Community)
    comm.id, comm.features = CID, {}
    crepo = AsyncMock(spec=CommunityRepository)
    crepo.get.return_value = comm
    return StoryService(StoryRepository(s), crepo, notify, CID), notify


async def test_ask_refuses_self_blocked_memorialized_and_caps_at_five(session):
    svc, notify = _svc(session)
    a, b, c = await _user(session), await _user(session), await _user(session)
    dead = await _user(session, memorialized_at=datetime.now(UTC))
    with pytest.raises(AppError):
        await svc.ask(a.id, a.id, "q?")
    with pytest.raises(NotFoundError):
        await svc.ask(a.id, dead.id, "q?")
    session.add(UserBlock(blocker_id=c.id, blocked_id=a.id, community_id=CID))
    await session.flush()
    with pytest.raises(NotFoundError):
        await svc.ask(a.id, c.id, "q?")
    with pytest.raises(NotFoundError):
        await svc.ask(c.id, a.id, "q?")
    for i in range(5):
        await svc.ask(a.id, b.id, f"q{i}")
    assert notify.notify.await_count == 5
    with pytest.raises(AppError) as exc:
        await svc.ask(a.id, b.id, "one too many")
    assert exc.value.code == "STORY_LIMIT"


async def test_decline_is_silent_and_asker_sees_open_then_expired(session):
    svc, notify = _svc(session)
    asker, teller, other = await _user(session), await _user(session), await _user(session)
    req = await svc.ask(asker.id, teller.id, "Tell me about the farm")
    notify.reset_mock()
    await svc.decline(req.id, teller.id)
    notify.notify.assert_not_awaited()
    assert (await svc.get(req.id, asker.id)).status == "open"
    assert (await svc.get(req.id, teller.id)).status == "declined"
    assert (await svc.list_for(teller.id)).incoming == []
    with pytest.raises(NotFoundError):
        await svc.get(req.id, other.id)
    row = await StoryRepository(session).get(req.id, CID)
    row.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    await session.flush()
    assert (await svc.get(req.id, asker.id)).status == "expired"
    assert (await svc.run_daily(datetime.now(UTC)))["expired"] == 1
    assert row.status == "expired"
    with pytest.raises(AppError):
        await svc.answer(req.id, teller.id, uuid.uuid4())


async def test_answer_links_post_and_notifies_asker_only_teller_may_answer(session):
    svc, notify = _svc(session)
    asker, teller = await _user(session), await _user(session)
    req = await svc.ask(asker.id, teller.id, "First job?")
    notify.reset_mock()
    mine, theirs = await _post(session, teller, audio=True), await _post(session, asker)
    with pytest.raises(NotFoundError):
        await svc.answer(req.id, asker.id, theirs.id)
    with pytest.raises(AppError):
        await svc.answer(req.id, teller.id, theirs.id)
    out = await svc.answer(req.id, teller.id, mine.id)
    assert out.status == "answered" and out.post_id == mine.id
    await session.refresh(mine)
    assert mine.story_request_id == req.id
    args = notify.notify.await_args.args
    assert args[0] == asker.id and args[1] == "story_answered"
    stories = await svc.stories_of(teller.id, asker.id)
    assert [i.question for i in stories.items] == ["First job?"]


async def test_reminder_sent_once_at_day_14(session):
    svc, notify = _svc(session)
    asker, teller = await _user(session), await _user(session)
    req = await svc.ask(asker.id, teller.id, "Q?")
    notify.reset_mock()
    assert (await svc.run_daily(datetime.now(UTC)))["reminded"] == 0
    row = await StoryRepository(session).get(req.id, CID)
    row.created_at = datetime.now(UTC) - timedelta(days=15)
    await session.flush()
    now = datetime.now(UTC)
    assert (await svc.run_daily(now))["reminded"] == 1
    assert (await svc.run_daily(now))["reminded"] == 0
    assert notify.notify.await_count == 1
    assert notify.notify.await_args.args[0] == teller.id


async def test_stories_tab_respects_post_visibility_and_blocks(session):
    svc, _ = _svc(session)
    author, viewer = await _user(session), await _user(session)
    await _post(session, author, "plain text")
    shown = await _post(session, author, "", audio=True)
    await _post(session, author, "", audio=True, visibility="private")
    items = (await svc.stories_of(author.id, viewer.id)).items
    assert [i.post["id"] for i in items] == [str(shown.id)]
    assert (await svc.stories_of(author.id, author.id)).items.__len__() == 2
    session.add(UserBlock(blocker_id=viewer.id, blocked_id=author.id, community_id=CID))
    await session.flush()
    assert (await svc.stories_of(author.id, viewer.id)).items == []
    assert await session.scalar(select(Post.id).where(Post.id == shown.id)) is not None


async def test_recap_pending_excludes_blocked_and_declined(session):
    svc, _ = _svc(session)
    teller, a, b, c = [await _user(session) for _ in range(4)]
    await svc.ask(a.id, teller.id, "from a")
    rb = await svc.ask(b.id, teller.id, "from b")
    await svc.ask(c.id, teller.id, "from c")
    await svc.decline(rb.id, teller.id)
    session.add(UserBlock(blocker_id=teller.id, blocked_id=c.id, community_id=CID))
    await session.flush()
    got = await svc.pending_for(teller.id, datetime.now(UTC))
    assert [q.question for q, _n in got] == ["from a"]
