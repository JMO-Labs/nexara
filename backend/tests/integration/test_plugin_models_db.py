"""
@file test_plugin_models_db.py
@brief DB-backed tests for Plugin/PluginData CRUD, soft-delete and scoping.
"""

import os
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.models.community import Community
from app.models.plugin import Plugin, PluginData

TEST_DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://nexara:nexara@localhost:5432/nexara_test",
)
C1 = uuid.UUID("00000000-0000-0000-0000-000000000001")


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


async def _second_community(session: AsyncSession) -> uuid.UUID:
    cid = uuid.uuid4()
    session.add(Community(id=cid, name=f"Other {cid.hex[:8]}"))
    await session.flush()
    return cid


async def test_insert_applies_server_defaults(session: AsyncSession):
    session.add(Plugin(id="p1", community_id=C1, name="P", version="1.0.0"))
    await session.flush()
    p = (await session.execute(select(Plugin).where(Plugin.id == "p1"))).scalar_one()
    await session.refresh(p)
    assert p.is_enabled is False
    assert p.permissions_granted == [] and p.settings == {}
    assert p.deleted_at is None and p.installed_at is not None


async def test_soft_delete_keeps_row(session: AsyncSession):
    from datetime import UTC, datetime

    session.add(Plugin(id="p2", community_id=C1, name="P", version="1"))
    await session.flush()
    p = (await session.execute(select(Plugin).where(Plugin.id == "p2"))).scalar_one()
    p.deleted_at = datetime.now(UTC)
    await session.flush()
    live = await session.execute(
        select(Plugin).where(Plugin.id == "p2", Plugin.deleted_at.is_(None))
    )
    assert live.scalar_one_or_none() is None
    anyrow = await session.execute(select(Plugin).where(Plugin.id == "p2"))
    assert anyrow.scalar_one().deleted_at is not None


async def test_plugin_data_crud(session: AsyncSession):
    session.add(Plugin(id="p3", community_id=C1, name="P", version="1"))
    await session.flush()
    row = PluginData(plugin_id="p3", community_id=C1, key="k", value_json={"n": 1})
    session.add(row)
    await session.flush()
    assert row.id is not None

    row.value_json = {"n": 2}
    await session.flush()
    got = (await session.execute(select(PluginData).where(PluginData.key == "k"))).scalar_one()
    assert got.value_json == {"n": 2}

    await session.delete(got)
    await session.flush()
    left = await session.execute(select(PluginData).where(PluginData.plugin_id == "p3"))
    assert left.first() is None


async def test_same_plugin_id_in_two_communities(session: AsyncSession):
    c2 = await _second_community(session)
    session.add_all(
        [
            Plugin(id="shared", community_id=C1, name="P", version="1"),
            Plugin(id="shared", community_id=c2, name="P", version="1"),
        ]
    )
    await session.flush()
    rows = (await session.execute(select(Plugin).where(Plugin.id == "shared"))).scalars().all()
    assert {r.community_id for r in rows} == {C1, c2}


async def test_duplicate_key_raises(session: AsyncSession):
    session.add(Plugin(id="p4", community_id=C1, name="P", version="1"))
    await session.flush()
    session.add(PluginData(plugin_id="p4", community_id=C1, key="dup", value_json=1))
    await session.flush()
    session.add(PluginData(plugin_id="p4", community_id=C1, key="dup", value_json=2))
    with pytest.raises(IntegrityError):
        await session.flush()
