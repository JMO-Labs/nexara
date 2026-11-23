"""
@file test_chore_advance_db.py
@brief Real-Postgres tests of ChoreService.advance and the due-scan queries.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401 — registers all mapped classes
from app.models.community import Community
from app.models.list import List, ListItem
from app.models.list_assignment import ListActivity, ListItemAssignment
from app.models.user import User
from app.repositories.chore_repo import ChoreRepository
from app.repositories.list_activity_repo import ListActivityRepository
from app.repositories.list_assignment_repo import ListAssignmentRepository
from app.repositories.list_item_repo import ListItemRepository
from app.repositories.list_repo import ListRepository
from app.services.chore_service import ChoreService
from app.services.list_activity_service import ListActivityService

DB_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://nexara:nexara@localhost:5432/nexara_test"
)
NOW = datetime(2026, 11, 22, 12, 0, tzinfo=UTC)


@pytest.fixture
async def s() -> AsyncIterator[AsyncSession]:
    """@brief Session on the test DB; seed rows are removed in teardown."""
    engine = create_async_engine(DB_URL)
    async with async_sessionmaker(engine, expire_on_commit=False)() as session:
        yield session
    await engine.dispose()


async def _seed(s: AsyncSession) -> dict:
    c = Community(name=f"chore-{uuid.uuid4().hex[:6]}")
    s.add(c)
    await s.flush()
    users = []
    for n in ("a", "b"):
        tag = uuid.uuid4().hex[:8]
        u = User(community_id=c.id, email=f"{n}_{tag}@x.dev", username=f"{n}_{tag}", display_name=n)
        s.add(u)
        users.append(u)
    await s.flush()
    a, b = users
    lst = List(community_id=c.id, owner_id=a.id, title="Chores", visibility="community")
    dead = List(
        community_id=c.id, owner_id=a.id, title="Old", visibility="community", deleted_at=NOW
    )
    s.add_all([lst, dead])
    await s.flush()
    due = NOW - timedelta(minutes=5)

    def mk(parent: List) -> ListItem:
        return ListItem(
            list_id=parent.id,
            values={"title": "Trash"},
            repeat="weekly",
            rotation=[a.id, b.id],
            rotation_index=0,
            next_due_at=due,
        )

    item, orphan = mk(lst), mk(dead)
    s.add_all([item, orphan])
    await s.flush()
    s.add(
        ListItemAssignment(
            community_id=c.id,
            item_id=item.id,
            list_id=lst.id,
            assignee_id=a.id,
            assigned_by=a.id,
            status="pending",
        )
    )
    await s.commit()
    return {
        "ids": ([lst.id, dead.id], [a.id, b.id], c.id),
        "c": c,
        "a": a,
        "b": b,
        "lst": lst,
        "dead": dead,
        "item": item,
        "orphan": orphan,
    }


async def _cleanup(s: AsyncSession, d: dict) -> None:
    await s.rollback()
    lists, users, cid = d["ids"]
    await s.execute(delete(List).where(List.id.in_(lists)))
    await s.execute(delete(User).where(User.id.in_(users)))
    await s.execute(delete(Community).where(Community.id == cid))
    await s.commit()


def _svc(s: AsyncSession, c: Community) -> ChoreService:
    lists = ListRepository(s)
    return ChoreService(
        ChoreRepository(s),
        ListItemRepository(s),
        lists,
        ListAssignmentRepository(s),
        ListActivityService(ListActivityRepository(s), lists, c.id),
        c,
    )


async def test_advance_rotates_once_and_parks_deleted_list_items(s: AsyncSession) -> None:
    d = await _seed(s)
    try:
        repo = ChoreRepository(s)
        due_ids = await repo.due_item_ids(NOW)
        assert d["item"].id in due_ids and d["orphan"].id not in due_ids
        assert await repo.lock_due(d["orphan"].id, NOW) is None

        svc = _svc(s, d["c"])
        item = await repo.lock_due(d["item"].id, NOW)
        assert item is not None
        due_before = item.next_due_at
        await svc.advance(item, NOW)
        await s.commit()

        active = (
            (
                await s.execute(
                    select(ListItemAssignment).where(
                        ListItemAssignment.item_id == d["item"].id,
                        ListItemAssignment.status.in_(("pending", "accepted")),
                    )
                )
            )
            .scalars()
            .all()
        )
        assert [r.assignee_id for r in active] == [d["b"].id]
        acts = (
            await s.execute(select(ListActivity).where(ListActivity.item_id == d["item"].id))
        ).scalars()
        missed = [x for x in acts if x.action == "missed"]
        assert len(missed) == 1 and missed[0].target_user_id == d["a"].id
        await s.refresh(item)
        assert item.next_due_at == due_before + timedelta(days=7)
        assert item.rotation_index == 1

        assert await repo.lock_due(d["item"].id, NOW) is None
        await svc.advance(item, NOW)
        await s.commit()
        assert item.rotation_index == 1 and item.next_due_at == due_before + timedelta(days=7)

        orphan = await s.get(ListItem, d["orphan"].id)
        assert orphan is not None
        await svc.advance(orphan, NOW)
        await s.commit()
        await s.refresh(orphan)
        assert orphan.next_due_at is None
    finally:
        await _cleanup(s, d)
