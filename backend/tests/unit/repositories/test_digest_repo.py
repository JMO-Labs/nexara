"""
@file test_digest_repo.py
@brief Unit tests for DigestRepository.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.dialects import postgresql

from app.models.notification_digest import NotificationDigestQueue
from app.repositories.digest_repo import DigestRepository


def _session() -> AsyncMock:
    s = AsyncMock()
    s.add = MagicMock()
    return s


async def test_enqueue_is_insert_on_conflict_do_nothing():
    s = _session()
    uid, nid = uuid.uuid4(), uuid.uuid4()
    await DigestRepository(s).enqueue(uid, "comment", nid)
    stmt = s.execute.await_args.args[0]
    sql = str(stmt.compile(dialect=postgresql.dialect()))
    assert "INSERT INTO notification_digest_queue" in sql
    assert "ON CONFLICT (user_id, notification_id) DO NOTHING" in sql


def test_model_matches_spec_schema():
    t = NotificationDigestQueue.__table__
    assert [c.name for c in t.primary_key.columns] == ["user_id", "notification_id"]
    assert "enqueued_at" in t.c
    assert "id" not in t.c
    assert {i.name for i in t.indexes} == {"digest_queue_drain_idx"}


async def test_drain_returns_ids_and_deletes():
    s = _session()
    ids = [uuid.uuid4(), uuid.uuid4()]
    res = MagicMock()
    res.scalars.return_value.all.return_value = ids
    s.execute.return_value = res
    out = await DigestRepository(s).drain(uuid.uuid4(), "comment")
    assert out == ids
    assert s.execute.await_count == 1  # single DELETE ... RETURNING


async def test_drain_idempotent_when_empty():
    s = _session()
    res = MagicMock()
    res.scalars.return_value.all.return_value = []
    s.execute.return_value = res
    repo = DigestRepository(s)
    assert await repo.drain(uuid.uuid4(), "x") == []
    assert await repo.drain(uuid.uuid4(), "x") == []


async def test_list_users_with_pending():
    s = _session()
    ids = [uuid.uuid4()]
    res = MagicMock()
    res.scalars.return_value.all.return_value = ids
    s.execute.return_value = res
    assert await DigestRepository(s).list_users_with_pending() == ids


async def test_list_pending_types():
    s = _session()
    res = MagicMock()
    res.scalars.return_value.all.return_value = ["a", "b"]
    s.execute.return_value = res
    assert await DigestRepository(s).list_pending_types(uuid.uuid4()) == ["a", "b"]
