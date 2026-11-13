"""
@file test_community_ai_config.py
@brief Real-Postgres tests: admin AI config persists to ``Community`` columns
       (what Sassybot reads) and the opt-out count is tenant-scoped.
"""

from __future__ import annotations

import os
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401 — registers all mapped classes
from app.models.community import Community
from app.models.user import User
from app.models.user_settings import UserSettings
from app.repositories.community_repo import CommunityRepository
from app.repositories.sassybot_repo import SassybotRepository
from app.repositories.settings_repo import SettingsRepository
from app.services.ai.admin_ai_service import AdminAIService

TEST_DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://nexara:nexara@localhost:5432/nexara_test",
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


async def _community(session: AsyncSession) -> uuid.UUID:
    c = Community(name=f"ai-{uuid.uuid4().hex[:6]}")
    session.add(c)
    await session.flush()
    return c.id


async def _user(session: AsyncSession, cid: uuid.UUID, allow: bool) -> None:
    tag = uuid.uuid4().hex[:8]
    u = User(community_id=cid, email=f"u{tag}@nexara.dev", username=f"u{tag}", display_name=tag)
    session.add(u)
    await session.flush()
    session.add(UserSettings(user_id=u.id, community_id=cid, allow_sassybot=allow))
    await session.flush()


def _service(session: AsyncSession, cid: uuid.UUID) -> AdminAIService:
    settings = SimpleNamespace(AI_PROVIDER="ollama", AI_DAILY_BUDGET_CENTS=200)
    return AdminAIService(
        CommunityRepository(session),
        SettingsRepository(session),
        cid,
        settings,
        AsyncMock(),
        lambda: None,
    )


async def test_defaults_come_from_community_columns(session):
    cid = await _community(session)
    cfg = await _service(session, cid).get_config()
    assert cfg["sassybot_enabled"] is True
    assert cfg["sass_level"] == 2
    assert cfg["probability"] == 15
    assert cfg["invoke_only"] is False


async def test_update_persists_to_community_seen_by_sassybot(session):
    cid = await _community(session)
    other = await _community(session)
    await _service(session, cid).update_config(
        {"sassybot_enabled": False, "sass_level": 3, "probability": 55, "invoke_only": True}
    )
    session.expire_all()
    seen = await SassybotRepository(session).get_community(cid)
    assert seen is not None
    assert seen.sassybot_enabled is False
    assert seen.sassybot_sass_level == 3
    assert seen.sassybot_probability == 55
    assert seen.sassybot_invoke_only is True
    untouched = await SassybotRepository(session).get_community(other)
    assert untouched is not None and untouched.sassybot_probability == 15


async def test_partial_update_keeps_other_columns(session):
    cid = await _community(session)
    cfg = await _service(session, cid).update_config({"probability": 40})
    assert cfg["probability"] == 40
    assert cfg["sass_level"] == 2


async def test_update_unknown_community_returns_none(session):
    assert await CommunityRepository(session).update_sassybot(uuid.uuid4(), {}) is None


async def test_opt_out_count_scoped_to_community(session):
    cid = await _community(session)
    other = await _community(session)
    await _user(session, cid, allow=False)
    await _user(session, cid, allow=False)
    await _user(session, cid, allow=True)
    await _user(session, other, allow=False)
    assert await SettingsRepository(session).count_sassybot_opt_outs(cid) == 2
    assert (await _service(session, cid).get_config())["opt_out_count"] == 2
