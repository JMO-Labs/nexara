"""
@file test_nudge_repo_unit.py
@brief Mocked-session tests for NudgeRepository (no database needed).
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

from app.models.nudge import Nudge
from app.repositories.nudge_repo import NudgeRepository

CID = uuid.uuid4()


def _repo(scalar=None, scalars=None) -> tuple[NudgeRepository, AsyncMock]:
    session = AsyncMock()
    result = MagicMock()
    result.scalar.return_value = scalar
    result.scalars.return_value.all.return_value = scalars or []
    session.execute.return_value = result
    session.add = MagicMock()
    return NudgeRepository(session), session


async def test_create_nudge_persists_row():
    repo, session = _repo()
    nudge = await repo.create_nudge(uuid.uuid4(), uuid.uuid4(), "user_initiated", CID)
    assert isinstance(nudge, Nudge)
    assert nudge.nudge_type == "user_initiated"
    session.add.assert_called_once_with(nudge)


async def test_has_recent_user_nudge_true_and_false():
    repo, _ = _repo(scalar=True)
    assert await repo.has_recent_user_nudge(uuid.uuid4(), uuid.uuid4(), CID) is True
    repo, _ = _repo(scalar=False)
    assert await repo.has_recent_user_nudge(uuid.uuid4(), uuid.uuid4(), CID) is False


async def test_is_blocked_true_and_false():
    repo, _ = _repo(scalar=True)
    assert await repo.is_blocked(uuid.uuid4(), uuid.uuid4(), CID) is True
    repo, _ = _repo(scalar=None)
    assert await repo.is_blocked(uuid.uuid4(), uuid.uuid4(), CID) is False


async def test_find_gentle_candidates_returns_ids():
    ids = [uuid.uuid4(), uuid.uuid4()]
    repo, session = _repo(scalars=ids)
    assert await repo.find_gentle_candidates(CID) == ids
    session.execute.assert_awaited_once()
