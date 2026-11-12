"""
@file test_birthday_repo.py
@brief Unit tests for BirthdayRepository query construction and result mapping.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

from app.repositories.birthday_repo import BirthdayRepository


def _repo(result: MagicMock) -> tuple[BirthdayRepository, AsyncMock]:
    session = AsyncMock()
    session.execute.return_value = result
    return BirthdayRepository(session), session


def _sql(session: AsyncMock) -> str:
    return str(session.execute.await_args.args[0])


async def test_list_community_ids_with_birthday_distinct_and_active():
    cids = [uuid.uuid4(), uuid.uuid4()]
    result = MagicMock()
    result.scalars.return_value.all.return_value = cids
    repo, session = _repo(result)

    assert await repo.list_community_ids_with_birthday(3, 14) == cids

    sql = _sql(session)
    assert "DISTINCT" in sql
    assert "users.deleted_at IS NULL" in sql
    assert "users.is_active IS true" in sql
    assert "month" in sql and "day" in sql


async def test_list_birthday_users_scoped_and_maps_pairs():
    user = MagicMock()
    result = MagicMock()
    result.all.return_value = [(user, "private")]
    repo, session = _repo(result)

    out = await repo.list_birthday_users(uuid.uuid4(), 3, 14)

    assert out == [(user, "private")]
    sql = _sql(session)
    assert "users.community_id" in sql
    assert "LEFT OUTER JOIN user_settings" in sql
    assert "coalesce" in sql.lower()
    assert "users.deleted_at IS NULL" in sql


async def test_list_member_ids_excludes_bots_and_inactive():
    ids = [uuid.uuid4()]
    result = MagicMock()
    result.scalars.return_value.all.return_value = ids
    repo, session = _repo(result)

    assert await repo.list_member_ids(uuid.uuid4()) == ids

    sql = _sql(session)
    assert "users.community_id" in sql
    assert "users.is_bot IS false" in sql
    assert "users.is_active IS true" in sql
    assert "users.deleted_at IS NULL" in sql


async def test_list_admin_ids_filters_admin_role():
    ids = [uuid.uuid4()]
    result = MagicMock()
    result.scalars.return_value.all.return_value = ids
    repo, session = _repo(result)

    assert await repo.list_admin_ids(uuid.uuid4()) == ids

    sql = _sql(session)
    assert "users.community_id" in sql
    assert "users.role" in sql
    assert "users.deleted_at IS NULL" in sql
