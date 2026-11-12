"""
@file test_plugin_repos.py
@brief Real-Postgres tests: PluginRepository and PluginApiKeyRepository scoping.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.models.community import Community
from app.models.plugin import Plugin, PluginApiKey
from app.repositories.plugin_key_repo import PluginApiKeyRepository
from app.repositories.plugin_repo import PluginRepository

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


async def _other_community(session: AsyncSession) -> uuid.UUID:
    cid = uuid.uuid4()
    session.add(Community(id=cid, name=f"Other {cid.hex[:8]}"))
    await session.flush()
    return cid


def _pid() -> str:
    return f"rp-{uuid.uuid4().hex[:8]}"


async def _plugin(
    repo: PluginRepository, pid: str, cid: uuid.UUID, deleted: bool = False
) -> Plugin:
    row = Plugin(id=pid, community_id=cid, name="P", version="1.0.0")
    if deleted:
        row.deleted_at = datetime.now(UTC)
    return await repo.save(row)


async def test_save_creates_db_row(session: AsyncSession) -> None:
    repo = PluginRepository(session)
    pid = _pid()
    await _plugin(repo, pid, C1)
    got = await repo.get(pid, C1)
    assert got is not None and got.installed_at is not None and got.is_enabled is False


async def test_list_excludes_other_communities_and_soft_deleted(session: AsyncSession) -> None:
    repo = PluginRepository(session)
    other = await _other_community(session)
    live, gone, foreign = _pid(), _pid(), _pid()
    await _plugin(repo, live, C1)
    await _plugin(repo, gone, C1, deleted=True)
    await _plugin(repo, foreign, other)
    ids = {p.id for p in await repo.list(C1)}
    assert live in ids
    assert gone not in ids and foreign not in ids
    assert [p.id for p in await repo.list(other)] == [foreign]


async def test_get_soft_deleted_only_with_include_deleted(session: AsyncSession) -> None:
    repo = PluginRepository(session)
    pid = _pid()
    await _plugin(repo, pid, C1, deleted=True)
    assert await repo.get(pid, C1) is None
    got = await repo.get(pid, C1, include_deleted=True)
    assert got is not None and got.deleted_at is not None


async def test_get_is_community_scoped(session: AsyncSession) -> None:
    repo = PluginRepository(session)
    other = await _other_community(session)
    pid = _pid()
    await _plugin(repo, pid, other)
    assert await repo.get(pid, C1) is None
    assert await repo.get(pid, C1, include_deleted=True) is None


async def test_revoke_all_only_touches_that_plugin_in_that_community(
    session: AsyncSession,
) -> None:
    prepo, krepo = PluginRepository(session), PluginApiKeyRepository(session)
    other = await _other_community(session)
    target, sibling = _pid(), _pid()
    await _plugin(prepo, target, C1)
    await _plugin(prepo, sibling, C1)
    await _plugin(prepo, target, other)

    async def mk(pid: str, cid: uuid.UUID) -> PluginApiKey:
        h = uuid.uuid4().hex
        return await krepo.create(plugin_id=pid, community_id=cid, key_hash=h, key_hint=h[:8])

    k1 = await mk(target, C1)
    k2 = await mk(target, C1)
    ks = await mk(sibling, C1)
    ko = await mk(target, other)

    await krepo.revoke_all(target, C1)

    assert k1.revoked_at is not None and k2.revoked_at is not None
    assert await krepo.active_keys_for_plugin_any(target, C1) == []
    assert [k.id for k in await krepo.active_keys_for_plugin_any(sibling, C1)] == [ks.id]
    assert [k.id for k in await krepo.active_keys_for_plugin_any(target, other)] == [ko.id]


async def test_active_keys_any_ignores_enablement(session: AsyncSession) -> None:
    prepo, krepo = PluginRepository(session), PluginApiKeyRepository(session)
    pid = _pid()
    await _plugin(prepo, pid, C1)  # is_enabled defaults to False
    k = await krepo.create(
        plugin_id=pid, community_id=C1, key_hash=uuid.uuid4().hex, key_hint="abcd"
    )
    assert await krepo.active_keys_for_plugin(pid, C1) == []
    assert [x.id for x in await krepo.active_keys_for_plugin_any(pid, C1)] == [k.id]
