"""
@file test_plugin_bot_exclusion.py
@brief Plugin bot users are hidden from user lists and login/OAuth lookups (real DB).
"""

from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401 — registers all mapped classes
from app.models.user import COMMUNITY_DEFAULT, User
from app.repositories.user_repo import UserRepository

TEST_DB_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://nexara:nexara@localhost:5432/nexara_test"
)
CID = uuid.UUID(COMMUNITY_DEFAULT)


@pytest.fixture
async def session():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        async with sess.begin():
            yield sess
            await sess.rollback()
    await engine.dispose()


async def test_bot_hidden_from_lists_and_auth_lookups(session: AsyncSession) -> None:
    tag = uuid.uuid4().hex[:6]
    bot = User(
        community_id=CID,
        email=f"bot{tag}+x@plugins.invalid",
        username=f"zbot{tag}",
        display_name="Bot",
        is_bot=True,
        oidc_sub=f"sub{tag}",
    )
    session.add(bot)
    await session.flush()
    repo = UserRepository(session)
    listed, _ = await repo.list_by_community(CID, limit=500)
    searched, _ = await repo.list_by_community_search(CID, search=f"zbot{tag}")
    assert bot.id in {u.id for u in listed}  # active bots stay @mentionable
    assert searched == []
    assert await repo.find_by_email(bot.email) is None
    assert await repo.find_by_oidc_sub(f"sub{tag}") is None
    assert await repo.email_exists(bot.email) is True  # still reserved
    assert (await repo.find_by_username(bot.username)) is not None  # profile/mention/uniqueness


async def _bot(session: AsyncSession, active: bool = True) -> User:
    tag = uuid.uuid4().hex[:6]
    bot = User(
        community_id=CID,
        email=f"b{tag}+x@plugins.invalid",
        username=f"qbot{tag}",
        display_name=f"Qbot {tag}",
        is_bot=True,
        is_active=active,
    )
    session.add(bot)
    await session.flush()
    return bot


async def test_mention_list_keeps_active_bots_only(session: AsyncSession) -> None:
    on, off = await _bot(session), await _bot(session, active=False)
    ids = {u.id for u in (await UserRepository(session).list_by_community(CID, limit=1000))[0]}
    assert on.id in ids and off.id not in ids


async def test_user_search_excludes_bots(session: AsyncSession) -> None:
    from app.repositories.search_repo import SearchRepository

    bot = await _bot(session)
    rows, _, total = await SearchRepository(session).search_users(
        bot.username, bot.username, CID, None, 20
    )
    assert bot.id not in {u.id for u, _ in rows}


async def test_chat_picker_and_others_exclude_bots(session: AsyncSession) -> None:
    from app.repositories.celebration_repo import CelebrationRepository
    from app.repositories.chat_context_repo import ChatContextRepository
    from app.repositories.storage_repo import StorageRepository

    bot = await _bot(session)
    viewer = User(
        community_id=CID,
        email=f"v{uuid.uuid4().hex[:6]}@x.dev",
        username=f"v{uuid.uuid4().hex[:6]}",
        display_name="V",
    )
    session.add(viewer)
    await session.flush()
    members, _ = await ChatContextRepository(session).members(viewer.id, CID, None, limit=500)
    assert bot.id not in {u.id for u in members}
    assert viewer.id in {u.id for u in members}
    assert await CelebrationRepository(session).celebratable_user(CID, viewer.id, bot.id) is None
    top = await StorageRepository(session).top_users(CID, 1000)
    assert bot.id not in {u.id for u in top}
