"""
@file test_digest_repo.py
@brief Unit tests for DigestRepository.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.notification_digest import NotificationDigestQueue
from app.repositories.digest_repo import DigestRepository


def _session() -> AsyncMock:
    s = AsyncMock()
    s.add = MagicMock()
    return s


async def test_enqueue_adds_row_and_flushes():
    s = _session()
    uid, nid = uuid.uuid4(), uuid.uuid4()
    row = await DigestRepository(s).enqueue(uid, "comment", nid)
    s.add.assert_called_once()
    assert isinstance(row, NotificationDigestQueue)
    assert (row.user_id, row.type_key, row.notification_id) == (uid, "comment", nid)
    s.flush.assert_awaited()


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
