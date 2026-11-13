"""
@file test_notification_repo_filters.py
@brief Real-Postgres tests: NotificationRepository filters, per-type counts, deletes.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.models.notification import Notification
from app.models.user import User
from app.repositories.notification_repo import NotificationRepository

TEST_DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://nexara:nexara@localhost:5432/nexara_test",
)
COMMUNITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


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


async def _user(session: AsyncSession) -> User:
    tag = uuid.uuid4().hex[:8]
    u = User(
        community_id=COMMUNITY_ID,
        email=f"nf_{tag}@nexara.dev",
        username=f"nf_{tag}",
        display_name="n",
    )
    session.add(u)
    await session.flush()
    return u


async def _notif(
    session: AsyncSession,
    user: User,
    type_: str,
    *,
    read: bool = False,
    age_days: int = 0,
) -> Notification:
    now = datetime.now(UTC)
    n = Notification(
        user_id=user.id,
        community_id=COMMUNITY_ID,
        type=type_,
        payload={"message": "m"},
        read_at=now if read else None,
        created_at=now - timedelta(days=age_days),
    )
    session.add(n)
    await session.flush()
    return n


async def test_list_filters_by_types_and_unread(session: AsyncSession) -> None:
    u = await _user(session)
    await _notif(session, u, "mention")
    await _notif(session, u, "mention", read=True)
    await _notif(session, u, "comment")
    repo = NotificationRepository(session)

    rows, _ = await repo.list_for_user(u.id, types=["mention"])
    assert {r.type for r in rows} == {"mention"} and len(rows) == 2

    rows, _ = await repo.list_for_user(u.id, types=["mention"], unread_only=True)
    assert len(rows) == 1


async def test_unread_counts_by_type_is_owner_scoped(session: AsyncSession) -> None:
    u, other = await _user(session), await _user(session)
    await _notif(session, u, "mention")
    await _notif(session, u, "mention")
    await _notif(session, u, "comment", read=True)
    await _notif(session, other, "mention")
    counts = await NotificationRepository(session).unread_counts_by_type(u.id)
    assert counts == {"mention": 2}


async def test_mark_all_read_by_types(session: AsyncSession) -> None:
    u = await _user(session)
    await _notif(session, u, "mention")
    await _notif(session, u, "comment")
    repo = NotificationRepository(session)
    assert await repo.mark_all_read(u.id, types=["mention"]) == 1
    assert await repo.unread_counts_by_type(u.id) == {"comment": 1}


async def test_delete_all_with_type_and_before(session: AsyncSession) -> None:
    u = await _user(session)
    await _notif(session, u, "mention", age_days=10)
    await _notif(session, u, "mention")
    await _notif(session, u, "comment", age_days=10)
    repo = NotificationRepository(session)
    cutoff = datetime.now(UTC) - timedelta(days=5)
    assert await repo.delete_all_for_user(u.id, types=["mention"], before=cutoff) == 1
    rows, _ = await repo.list_for_user(u.id)
    assert len(rows) == 2


async def test_delete_one_owner_isolation(session: AsyncSession) -> None:
    u, other = await _user(session), await _user(session)
    n = await _notif(session, u, "mention")
    repo = NotificationRepository(session)
    assert await repo.delete_one(other.id, n.id) is False
    assert await repo.delete_one(u.id, n.id) is True
    assert await repo.delete_one(u.id, n.id) is False
