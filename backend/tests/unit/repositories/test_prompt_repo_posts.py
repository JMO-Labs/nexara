"""
@file test_prompt_repo_posts.py
@brief Unit tests for PromptRepository.get_by_ids and get_prompt_post.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.dialects import postgresql

from app.repositories.prompt_repo import PromptRepository

COMMUNITY_ID = uuid.uuid4()


def _repo(scalar_one=None, scalars=None) -> tuple[PromptRepository, AsyncMock]:
    """@brief Build a repo over a mock session returning the given result."""
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = scalar_one
    result.scalars.return_value.all.return_value = scalars or []
    session.execute.return_value = result
    return PromptRepository(session), session


def _sql(session: AsyncMock) -> str:
    """@brief Compile the statement last passed to session.execute."""
    stmt = session.execute.call_args.args[0]
    return str(stmt.compile(dialect=postgresql.dialect()))


@pytest.mark.asyncio
async def test_get_by_ids_empty_short_circuits():
    """@brief Empty id list returns [] without querying."""
    repo, session = _repo()
    assert await repo.get_by_ids([], COMMUNITY_ID) == []
    session.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_by_ids_scopes_to_community():
    """@brief Non-empty ids query with IN and community filter."""
    prompts = [MagicMock(), MagicMock()]
    repo, session = _repo(scalars=prompts)
    out = await repo.get_by_ids([uuid.uuid4(), uuid.uuid4()], COMMUNITY_ID)
    assert out == prompts
    sql = _sql(session)
    assert "IN" in sql and "community_id" in sql


@pytest.mark.asyncio
async def test_get_prompt_post_without_community():
    """@brief No community arg means no community filter."""
    pp = MagicMock()
    repo, session = _repo(scalar_one=pp)
    assert await repo.get_prompt_post(uuid.uuid4()) is pp
    assert "community_id" not in _sql(session)


@pytest.mark.asyncio
async def test_get_prompt_post_with_community_filters():
    """@brief Community arg adds a community_id filter; miss returns None."""
    repo, session = _repo(scalar_one=None)
    assert await repo.get_prompt_post(uuid.uuid4(), COMMUNITY_ID) is None
    assert "community_id" in _sql(session)
