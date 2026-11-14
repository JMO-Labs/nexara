"""
@file test_notification_repo_filters.py
@brief Unit tests: NotificationRepository filters, counts, mark/delete (nexara#355).
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.dialects import postgresql

from app.repositories.notification_repo import NotificationRepository

USER = uuid.uuid4()


def _sql(stmt: object) -> str:
    return str(
        stmt.compile(  # type: ignore[attr-defined]
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    ).lower()


def _session(**result_attrs: object) -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    result = MagicMock()
    for k, v in result_attrs.items():
        setattr(result, k, v)
    session.execute = AsyncMock(return_value=result)
    return session


def _stmt(session: AsyncMock) -> str:
    return _sql(session.execute.await_args.args[0])


class TestListForUser:
    async def test_types_and_unread_filters_applied(self) -> None:
        session = _session()
        session.execute.return_value.scalars.return_value.all.return_value = []
        await NotificationRepository(session).list_for_user(
            USER, types=["mention"], unread_only=True
        )
        sql = _stmt(session)
        assert "notifications.type in ('mention')" in sql
        assert "read_at is null" in sql


class TestUnreadCounts:
    async def test_groups_by_type_and_maps_ints(self) -> None:
        session = _session()
        session.execute.return_value.all.return_value = [("mention", 2), ("comment", 1)]
        counts = await NotificationRepository(session).unread_counts_by_type(USER)
        assert counts == {"mention": 2, "comment": 1}
        sql = _stmt(session)
        assert "group by notifications.type" in sql
        assert "read_at is null" in sql


class TestUnreadCount:
    async def test_counts_unread_rows(self) -> None:
        session = _session()
        session.execute.return_value.scalar_one.return_value = 3
        assert await NotificationRepository(session).get_unread_count(USER) == 3
        assert "read_at is null" in _stmt(session)


class TestMarkAllRead:
    async def test_types_filter_and_count(self) -> None:
        n = MagicMock()
        session = _session()
        session.execute.return_value.scalars.return_value.all.return_value = [n]
        count = await NotificationRepository(session).mark_all_read(USER, types=["mention"])
        assert count == 1
        assert n.read_at is not None
        assert "notifications.type in ('mention')" in _stmt(session)


class TestDeleteAllForUser:
    async def test_types_and_before_filters(self) -> None:
        from datetime import UTC, datetime

        session = _session(rowcount=4)
        deleted = await NotificationRepository(session).delete_all_for_user(
            USER, types=["mention"], before=datetime(2026, 1, 1, tzinfo=UTC)
        )
        assert deleted == 4
        sql = _stmt(session)
        assert "notifications.type in ('mention')" in sql
        assert "created_at <" in sql


class TestDeleteOne:
    async def test_true_when_row_deleted(self) -> None:
        session = _session(rowcount=1)
        assert await NotificationRepository(session).delete_one(USER, uuid.uuid4()) is True
        assert _stmt(session).startswith("delete from notifications")

    async def test_false_when_missing(self) -> None:
        session = _session(rowcount=0)
        assert await NotificationRepository(session).delete_one(USER, uuid.uuid4()) is False
