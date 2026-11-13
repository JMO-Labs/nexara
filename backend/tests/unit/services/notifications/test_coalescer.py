"""
@file test_coalescer.py
@brief Unit tests for group-key coalescing (nexara#81).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.dialects import postgresql

import app.repositories.notification_repo as repo_mod
import app.services.notifications.types  # noqa: F401  (registers built-ins)
from app.models.notification import Notification
from app.repositories.notification_repo import NotificationRepository
from app.services.notifications import registry
from app.services.notifications.coalescer import compose_group_key

USER = uuid.uuid4()
COMMUNITY = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _session(existing: Notification | None = None) -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = existing
    session.execute = AsyncMock(return_value=result)
    return session


class TestComposeGroupKey:
    def test_key_when_window_and_target(self) -> None:
        t = registry.get("comment")
        assert compose_group_key(t, {"target_id": "p1"}) == "comment:p1"

    def test_none_without_window(self) -> None:
        t = registry.get("mention")
        assert compose_group_key(t, {"target_id": "p1"}) is None

    def test_none_without_target(self) -> None:
        t = registry.get("comment")
        assert compose_group_key(t, {}) is None
        assert compose_group_key(t, {"target_id": None}) is None


class TestUpsertGrouped:
    async def test_first_event_creates_row(self) -> None:
        session = _session(None)
        actor = uuid.uuid4()
        n = await NotificationRepository(session).upsert_grouped(
            USER,
            "comment",
            {"a": 1},
            group_key="comment:p1",
            actor_id=actor,
            community_id=COMMUNITY,
            group_window_seconds=300,
        )
        session.add.assert_called_once()
        assert n.count == 1
        assert n.actor_ids == [actor]
        assert n.group_key == "comment:p1"

    async def test_second_within_window_increments(self) -> None:
        a1, a2 = uuid.uuid4(), uuid.uuid4()
        existing = Notification(
            user_id=USER,
            community_id=COMMUNITY,
            type="comment",
            payload={"a": 1},
            group_key="comment:p1",
            count=1,
            actor_ids=[a1],
        )
        session = _session(existing)
        n = await NotificationRepository(session).upsert_grouped(
            USER,
            "comment",
            {"a": 2},
            group_key="comment:p1",
            actor_id=a2,
            community_id=COMMUNITY,
            group_window_seconds=300,
        )
        assert n is existing
        assert n.count == 2
        assert n.actor_ids == [a1, a2]
        assert n.payload == {"a": 2}
        session.add.assert_not_called()

    async def test_same_actor_deduped(self) -> None:
        a1 = uuid.uuid4()
        existing = Notification(
            user_id=USER,
            community_id=COMMUNITY,
            type="comment",
            payload={},
            group_key="k",
            count=1,
            actor_ids=[a1],
        )
        n = await NotificationRepository(_session(existing)).upsert_grouped(
            USER,
            "comment",
            {},
            group_key="k",
            actor_id=a1,
            community_id=COMMUNITY,
            group_window_seconds=300,
        )
        assert n.count == 2
        assert n.actor_ids == [a1]

    async def test_select_filters_window_and_skip_locked(self) -> None:
        session = _session(None)
        await NotificationRepository(session).upsert_grouped(
            USER,
            "comment",
            {},
            group_key="k",
            actor_id=None,
            community_id=COMMUNITY,
            group_window_seconds=300,
        )
        stmt = session.execute.call_args[0][0]
        sql = str(stmt.compile(dialect=postgresql.dialect())).lower()
        assert "for update skip locked" in sql
        assert "read_at is null" in sql
        assert "dismissed_at is null" in sql
        assert "created_at >=" in sql
        assert "community_id =" in sql
        assert COMMUNITY in stmt.compile(dialect=postgresql.dialect()).params.values()

    async def test_stale_row_outside_window_creates_new(self, monkeypatch) -> None:
        now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

        class _FrozenDT(datetime):
            @classmethod
            def now(cls, tz=None):  # noqa: ANN001, ANN206
                return now

        monkeypatch.setattr(repo_mod, "datetime", _FrozenDT)
        session = _session(None)
        actor = uuid.uuid4()
        n = await NotificationRepository(session).upsert_grouped(
            USER,
            "comment",
            {},
            group_key="k",
            actor_id=actor,
            community_id=COMMUNITY,
            group_window_seconds=300,
        )
        stmt = session.execute.call_args[0][0]
        params = stmt.compile(dialect=postgresql.dialect()).params
        assert now - timedelta(seconds=300) in params.values()
        session.add.assert_called_once()
        assert n.count == 1
        assert n.actor_ids == [actor]

    async def test_no_group_key_always_inserts_without_select(self) -> None:
        session = _session(MagicMock())
        n = await NotificationRepository(session).upsert_grouped(
            USER,
            "mention",
            {},
            group_key=None,
            actor_id=None,
            community_id=COMMUNITY,
            group_window_seconds=None,
        )
        session.execute.assert_not_awaited()
        session.add.assert_called_once()
        assert n.count == 1
