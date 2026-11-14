"""
@file test_suggestion_repo.py
@brief Unit tests for SuggestionRepository with a mocked session.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.dialects import postgresql

from app.core.exceptions import ConflictError, NotFoundError
from app.models.suggestion import Suggestion
from app.repositories.suggestion_repo import SNIPPET_LEN, SuggestionRepository

CID = uuid.uuid4()


def _repo(rows: list | None = None) -> tuple[SuggestionRepository, AsyncMock]:
    session = AsyncMock()
    session.add = MagicMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = rows or []
    session.execute = AsyncMock(return_value=result)
    return SuggestionRepository(session), session


def _sql(session: AsyncMock) -> str:
    stmt = session.execute.await_args.args[0]
    return str(stmt.compile(dialect=postgresql.dialect()))


async def test_create_builds_suggestion():
    repo, session = _repo()
    s = await repo.create(CID, "prompt", {"text": "hi"})
    assert s.type == "prompt" and s.community_id == CID and s.content == {"text": "hi"}
    session.add.assert_called_once_with(s)


async def test_list_pending_filters_and_type():
    repo, session = _repo(["x"])
    assert await repo.list_pending(CID, "poll", 3, 2) == ["x"]
    sql = _sql(session)
    assert "approved_at IS NULL" in sql and "rejected_at IS NULL" in sql
    assert "suggestions.type =" in sql and "LIMIT" in sql and "OFFSET" in sql


async def test_list_pending_without_type():
    repo, session = _repo()
    await repo.list_pending(CID)
    assert "suggestions.type =" not in _sql(session)


async def test_approve_sets_fields():
    repo, session = _repo()
    s = MagicMock(spec=Suggestion, approved_at=None, rejected_at=None)
    repo.get_by_id = AsyncMock(return_value=s)
    uid = uuid.uuid4()
    assert await repo.approve(uuid.uuid4(), uid, CID) is s
    assert s.approved_by == uid and s.approved_at is not None
    session.flush.assert_awaited()
    session.refresh.assert_awaited_with(s)


async def test_reject_sets_fields():
    repo, session = _repo()
    s = MagicMock(spec=Suggestion, approved_at=None, rejected_at=None)
    repo.get_by_id = AsyncMock(return_value=s)
    assert await repo.reject(uuid.uuid4(), CID) is s
    assert s.rejected_at is not None
    session.refresh.assert_awaited_with(s)


async def test_not_found():
    repo, _ = _repo()
    repo.get_by_id = AsyncMock(return_value=None)
    with pytest.raises(NotFoundError):
        await repo.approve(uuid.uuid4(), uuid.uuid4(), CID)


@pytest.mark.parametrize("field", ["approved_at", "rejected_at"])
async def test_already_reviewed_conflicts(field):
    repo, _ = _repo()
    s = MagicMock(spec=Suggestion, approved_at=None, rejected_at=None)
    setattr(s, field, datetime.now(UTC))
    repo.get_by_id = AsyncMock(return_value=s)
    with pytest.raises(ConflictError):
        await repo.reject(uuid.uuid4(), CID)


async def test_recent_post_snippets_truncates_and_scopes():
    repo, session = _repo(["a" * 500, "b"])
    out = await repo.recent_post_snippets(CID, 2)
    assert out == ["a" * SNIPPET_LEN, "b"]
    sql = _sql(session)
    assert "visibility" in sql and "recipient_id IS NULL" in sql and "deleted_at IS NULL" in sql


async def test_top_interests():
    repo, session = _repo(["hiking"])
    assert await repo.top_interests(CID, 5) == ["hiking"]
    assert "GROUP BY" in _sql(session)


async def test_upcoming_event_titles():
    repo, session = _repo(["picnic"])
    assert await repo.upcoming_event_titles(CID, 5) == ["picnic"]
    sql = _sql(session)
    assert "starts_at" in sql and "source_removed" in sql
