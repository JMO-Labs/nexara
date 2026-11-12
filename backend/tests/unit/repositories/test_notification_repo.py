"""
@file test_notification_repo.py
@brief Unit tests for NotificationRepository list_active/dismiss/dismiss_all/upsert_grouped (nexara#309).
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.dialects import postgresql

from app.core.exceptions import NotFoundError
from app.models.notification import Notification
from app.repositories.notification_repo import NotificationRepository

USER = uuid.uuid4()
COMMUNITY = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _sql(stmt: object) -> str:
    return str(
        stmt.compile(  # type: ignore[attr-defined]
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    ).lower()


def _session(scalar: object = None, rows: list | None = None, rowcount: int = 0) -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = scalar
    result.scalars.return_value.all.return_value = rows or []
    result.rowcount = rowcount
    session.execute = AsyncMock(return_value=result)
    return session


class TestListActive:
    async def test_filters_undismissed_newest_first(self) -> None:
        rows = [MagicMock(spec=Notification)]
        session = _session(rows=rows)
        out = await NotificationRepository(session).list_active(USER, limit=5)
        assert out == rows
        sql = _sql(session.execute.call_args[0][0])
        assert "dismissed_at is null" in sql
        assert str(USER) in sql
        assert "order by notifications.created_at desc" in sql
        assert "limit 5" in sql


class TestDismiss:
    async def test_sets_dismissed_at_for_owner(self) -> None:
        n = MagicMock(spec=Notification)
        n.dismissed_at = None
        session = _session(scalar=n)
        await NotificationRepository(session).dismiss(USER, uuid.uuid4())
        assert n.dismissed_at is not None
        session.flush.assert_awaited()
        assert str(USER) in _sql(session.execute.call_args[0][0])

    async def test_not_found_or_not_owner_raises(self) -> None:
        session = _session(scalar=None)
        with pytest.raises(NotFoundError):
            await NotificationRepository(session).dismiss(USER, uuid.uuid4())


class TestDismissAll:
    async def test_updates_active_rows_returns_count(self) -> None:
        session = _session(rowcount=3)
        count = await NotificationRepository(session).dismiss_all(USER)
        assert count == 3
        sql = _sql(session.execute.call_args[0][0])
        assert sql.startswith("update notifications")
        assert "dismissed_at is null" in sql
        assert str(USER) in sql


class TestUpsertGrouped:
    async def test_no_group_key_plain_insert_with_actor(self) -> None:
        session = _session()
        actor = uuid.uuid4()
        n = await NotificationRepository(session).upsert_grouped(
            user_id=USER,
            type="comment",
            payload={"m": 1},
            community_id=COMMUNITY,
            group_key=None,
            actor_id=actor,
        )
        added = session.add.call_args[0][0]
        assert added is n
        assert n.count == 1
        assert n.actor_ids == [actor]
        assert n.group_key is None

    async def test_no_actor_empty_actor_ids(self) -> None:
        session = _session()
        n = await NotificationRepository(session).upsert_grouped(
            user_id=USER, type="x", payload={}, community_id=COMMUNITY
        )
        assert n.actor_ids == []
        assert n.count == 1
