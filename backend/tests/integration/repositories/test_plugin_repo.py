"""
@file test_plugin_repo.py
@brief Real-Postgres tests for PluginRepository.
"""

from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.models.community import Community
from app.models.plugin import PluginCommunity
from app.models.post import Comment, Post, Reaction
from app.models.user import User
from app.repositories.plugin_repo import REMOVED_COMMENT, PluginRepository

TEST_DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://nexara:nexara@localhost:5432/nexara_test",
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


async def _user(session: AsyncSession, name: str) -> User:
    u = User(
        community_id=CID,
        email=f"pl_{name}_{uuid.uuid4().hex[:6]}@nexara.dev",
        username=f"pl_{name}_{uuid.uuid4().hex[:6]}",
        display_name=name,
        is_bot=True,
    )
    session.add(u)
    await session.flush()
    return u


async def _community(session: AsyncSession) -> uuid.UUID:
    c = Community(name=f"pl-{uuid.uuid4().hex[:6]}")
    session.add(c)
    await session.flush()
    return c.id


async def _setup(
    session: AsyncSession,
    *,
    status: str = "running",
    enabled: bool = True,
    events=("post.created",),
):
    repo = PluginRepository(session)
    inst = await repo.create_install(
        plugin_id=f"io.t.{uuid.uuid4().hex[:8]}",
        version="1.0.0",
        manifest={"events": list(events)},
        status=status,
    )
    pc = await repo.upsert_community(
        PluginCommunity(install_id=inst.id, community_id=CID, enabled=enabled)
    )
    return repo, inst, pc


async def test_resolve_token_ok(session: AsyncSession) -> None:
    repo, inst, _ = await _setup(session)
    h = uuid.uuid4().hex
    await repo.add_token(inst.id, CID, h)
    res = await repo.resolve_token(h)
    assert res is not None and res[1].id == inst.id
    assert await repo.resolve_token("nope") is None


async def test_resolve_token_rejects_revoked(session: AsyncSession) -> None:
    repo, inst, _ = await _setup(session)
    h = uuid.uuid4().hex
    await repo.add_token(inst.id, CID, h)
    await repo.revoke_tokens(inst.id, CID)
    assert await repo.resolve_token(h) is None


async def test_resolve_token_rejects_disabled_community(session: AsyncSession) -> None:
    repo, inst, _ = await _setup(session, enabled=False)
    h = uuid.uuid4().hex
    await repo.add_token(inst.id, CID, h)
    assert await repo.resolve_token(h) is None


async def test_resolve_token_rejects_non_running_install(session: AsyncSession) -> None:
    repo, inst, _ = await _setup(session, status="disabled")
    h = uuid.uuid4().hex
    await repo.add_token(inst.id, CID, h)
    assert await repo.resolve_token(h) is None


async def test_list_enabled_for_event_filters_by_event(session: AsyncSession) -> None:
    repo, inst, _ = await _setup(session, events=("post.created",))
    assert [i.id for i, _ in await repo.list_enabled_for_event(CID, "post.created")] == [inst.id]
    assert await repo.list_enabled_for_event(CID, "comment.created") == []


async def test_list_enabled_for_event_requires_running_and_enabled(session: AsyncSession) -> None:
    await _setup(session, status="failed")
    await _setup(session, enabled=False)
    assert await repo_list(session) == []


async def repo_list(session: AsyncSession):
    return await PluginRepository(session).list_enabled_for_event(CID, "post.created")


async def test_user_pref_roundtrip(session: AsyncSession) -> None:
    repo, inst, _ = await _setup(session)
    u = await _user(session, "p")
    assert await repo.get_user_pref(inst.id, u.id, CID) == {}
    await repo.set_user_pref(inst.id, u.id, CID, {"a": 1})
    await repo.set_user_pref(inst.id, u.id, CID, {"a": 2})
    assert await repo.get_user_pref(inst.id, u.id, CID) == {"a": 2}


async def test_user_pref_isolated_per_community(session: AsyncSession) -> None:
    repo, inst, _ = await _setup(session)
    u = await _user(session, "p")
    other = await _community(session)
    await repo.set_user_pref(inst.id, u.id, CID, {"a": 1})
    await repo.set_user_pref(inst.id, u.id, other, {"a": 2})
    assert await repo.get_user_pref(inst.id, u.id, CID) == {"a": 1}
    assert await repo.get_user_pref(inst.id, u.id, other) == {"a": 2}


async def test_resolve_token_scoped_to_its_community(session: AsyncSession) -> None:
    repo, inst, _ = await _setup(session)
    other = await _community(session)
    await repo.upsert_community(
        PluginCommunity(install_id=inst.id, community_id=other, enabled=False)
    )
    h = uuid.uuid4().hex
    await repo.add_token(inst.id, other, h)  # community B disabled
    assert await repo.resolve_token(h) is None
    await repo.upsert_community(
        PluginCommunity(install_id=inst.id, community_id=other, enabled=True)
    )
    res = await repo.resolve_token(h)
    assert res is not None and res[0].community_id == other and res[2].community_id == other


async def test_soft_delete_bot_content_keeps_human_replies(session: AsyncSession) -> None:
    repo = PluginRepository(session)
    bot, human = await _user(session, "bot"), await _user(session, "human")
    hp = Post(community_id=CID, author_id=human.id, content="hi")
    session.add(hp)
    await session.flush()
    bc = Comment(community_id=CID, post_id=hp.id, author_id=bot.id, content="roast")
    session.add(bc)
    await session.flush()
    reply = Comment(
        community_id=CID, post_id=hp.id, author_id=human.id, parent_id=bc.id, content="lol"
    )
    session.add(reply)
    await session.flush()
    await repo.soft_delete_bot_content(bot.id)
    await session.refresh(reply)
    await session.refresh(bc)
    assert reply.content == "lol" and bc.content == REMOVED_COMMENT


async def test_soft_delete_bot_content_hides_posts_and_comments(session: AsyncSession) -> None:
    repo = PluginRepository(session)
    bot, human = await _user(session, "bot"), await _user(session, "human")
    bp = Post(community_id=CID, author_id=bot.id, content="roast")
    hp = Post(community_id=CID, author_id=human.id, content="hi")
    session.add_all([bp, hp])
    await session.flush()
    session.add_all(
        [
            Comment(community_id=CID, post_id=hp.id, author_id=bot.id, content="c"),
            Comment(community_id=CID, post_id=hp.id, author_id=human.id, content="keep"),
            Reaction(
                community_id=CID, user_id=bot.id, target_type="post", target_id=hp.id, emoji="x"
            ),
            Reaction(
                community_id=CID, user_id=human.id, target_type="post", target_id=hp.id, emoji="x"
            ),
        ]
    )
    await session.flush()
    assert await repo.soft_delete_bot_content(bot.id) == 3
    await session.refresh(bp)
    await session.refresh(hp)
    assert bp.deleted_at is not None and hp.deleted_at is None
    comments = (await session.execute(select(Comment.content))).scalars().all()
    assert "c" not in comments and "keep" in comments and REMOVED_COMMENT in comments
    reacts = (await session.execute(select(Reaction.user_id))).scalars().all()
    assert bot.id not in reacts and human.id in reacts
