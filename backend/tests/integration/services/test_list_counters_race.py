"""
@file test_list_counters_race.py
@brief Real-Postgres race tests: list counters stay exact under concurrent writes.

Each concurrent call runs in its own session/transaction, so the row lock in
``lock_item_for_update`` and the atomic ``increment_counters`` UPDATE are what
keep ``item_count`` / ``completed_count`` exact. Seed data is committed (other
sessions must see it) and removed in teardown.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401 — registers all mapped classes
from app.core.exceptions import AppError
from app.models.community import Community
from app.models.list import List, ListItem
from app.models.user import User
from app.repositories.list_completion_repo import ListCompletionRepository
from app.repositories.list_item_repo import ListItemRepository
from app.repositories.list_repo import ListRepository
from app.services.list_completion_service import ListCompletionService
from app.services.list_field_registry import ListFieldRegistry
from app.services.list_items_service import ListItemService

TEST_DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://nexara:nexara@localhost:5432/nexara_test",
)
N = 20

Factory = async_sessionmaker[AsyncSession]


@pytest.fixture
async def factory() -> AsyncIterator[Factory]:
    """@brief Session factory on a pool large enough for N concurrent sessions."""
    engine = create_async_engine(TEST_DB_URL, echo=False, pool_size=N + 2, max_overflow=5)
    yield async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    await engine.dispose()


@pytest.fixture
async def seeded(factory: Factory) -> AsyncIterator[dict[str, Any]]:
    """@brief Committed community, owner and empty community-visible list."""
    async with factory() as s, s.begin():
        c = Community(name=f"race-{uuid.uuid4().hex[:6]}")
        s.add(c)
        await s.flush()
        tag = uuid.uuid4().hex[:8]
        u = User(
            community_id=c.id,
            email=f"race_{tag}@nexara.dev",
            username=f"race_{tag}",
            display_name="race",
        )
        s.add(u)
        await s.flush()
        lst = List(community_id=c.id, owner_id=u.id, title="Race", visibility="community")
        s.add(lst)
        await s.flush()
        data = {"cid": c.id, "uid": u.id, "list_id": lst.id}
    yield data
    async with factory() as s, s.begin():
        await s.execute(delete(List).where(List.id == data["list_id"]))
        await s.execute(delete(User).where(User.id == data["uid"]))
        await s.execute(delete(Community).where(Community.id == data["cid"]))


def _completion_svc(s: AsyncSession, cid: uuid.UUID) -> ListCompletionService:
    return ListCompletionService(
        ListItemRepository(s),
        ListRepository(s),
        ListCompletionRepository(s),
        ListFieldRegistry(),
        AsyncMock(),
        AsyncMock(),
        cid,
    )


async def _create_item(factory: Factory, d: dict[str, Any], pos: int) -> uuid.UUID:
    """@brief Create one item via ListItemService in its own transaction."""
    async with factory() as s, s.begin():
        svc = ListItemService(ListItemRepository(s), ListRepository(s), ListFieldRegistry())
        item = await svc.create(d["cid"], d["list_id"], d["uid"], {}, position=pos)
        return item.id


async def _complete(factory: Factory, d: dict[str, Any], item_id: uuid.UUID) -> ListItem:
    """@brief Complete one item via ListCompletionService in its own transaction."""
    async with factory() as s, s.begin():
        return await _completion_svc(s, d["cid"]).complete_item(item_id, d["uid"])


async def _counts(factory: Factory, list_id: uuid.UUID) -> tuple[int, int]:
    async with factory() as s:
        row = (
            await s.execute(select(List.item_count, List.completed_count).where(List.id == list_id))
        ).one()
        return int(row[0]), int(row[1])


async def test_concurrent_completes_on_distinct_items_keep_counters_exact(
    factory: Factory, seeded: dict[str, Any]
) -> None:
    """@brief N concurrent creates then N concurrent completes -> counters == N."""
    item_ids = await asyncio.gather(*(_create_item(factory, seeded, i) for i in range(N)))
    assert len(set(item_ids)) == N

    results = await asyncio.gather(
        *(_complete(factory, seeded, iid) for iid in item_ids), return_exceptions=True
    )

    assert [r for r in results if isinstance(r, BaseException)] == []
    item_count, completed_count = await _counts(factory, seeded["list_id"])
    assert item_count == N
    assert completed_count == N


async def test_concurrent_completes_on_same_item_count_once(
    factory: Factory, seeded: dict[str, Any]
) -> None:
    """
    @brief Two concurrent completes of one item: exactly one takes effect.

    The service treats an already-completed item as a no-op (see
    ``test_already_completed_is_noop``), so the loser may return the item
    rather than raise. Either way at most one call may fail, and only with
    ``AppError``; ``completed_count`` must grow by exactly 1.
    """
    item_id = await _create_item(factory, seeded, 0)
    _, before = await _counts(factory, seeded["list_id"])

    results = await asyncio.gather(
        _complete(factory, seeded, item_id),
        _complete(factory, seeded, item_id),
        return_exceptions=True,
    )

    errors = [r for r in results if isinstance(r, BaseException)]
    assert len(errors) <= 1
    assert all(isinstance(e, AppError) for e in errors), errors
    assert any(isinstance(r, ListItem) and r.completed for r in results)
    _, after = await _counts(factory, seeded["list_id"])
    assert after == before + 1
