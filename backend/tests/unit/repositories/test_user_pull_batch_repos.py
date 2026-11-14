"""@file Tests for batched lookups used by UserPullResolver (scoping, soft-delete, blocks)."""

import uuid
from unittest.mock import AsyncMock, MagicMock

from app.repositories.list_item_repo import ListItemRepository
from app.repositories.settings_repo import SettingsRepository
from app.repositories.user_repo import UserRepository

CID = uuid.uuid4()


def _session(rows=None):
    s = AsyncMock()
    r = MagicMock()
    r.scalars.return_value.all.return_value = rows or []
    s.execute.return_value = r
    return s


def _sql(s):
    return str(s.execute.await_args.args[0])


async def test_list_items_get_many_scoped():
    s = _session(["x"])
    out = await ListItemRepository(s).get_many(uuid.uuid4(), [uuid.uuid4()], CID)
    sql = _sql(s)
    assert out == ["x"]
    assert "list_item.list_id" in sql and "list.community_id" in sql
    assert "list_item.deleted_at IS NULL" in sql and "list.deleted_at IS NULL" in sql


async def test_users_get_many_scoped_and_block_filtered():
    s = _session()
    await UserRepository(s).get_many([uuid.uuid4()], CID, viewer_id=uuid.uuid4())
    sql = _sql(s)
    assert "users.community_id" in sql and "users.deleted_at IS NULL" in sql
    assert "user_blocks" in sql and "NOT IN" in sql


async def test_settings_get_many_scoped():
    s = _session()
    await SettingsRepository(s).get_many([uuid.uuid4()], CID)
    sql = _sql(s)
    assert "user_settings.user_id IN" in sql and "user_settings.community_id" in sql


async def test_empty_ids_skip_queries():
    s = _session()
    assert await ListItemRepository(s).get_many(uuid.uuid4(), [], CID) == []
    assert await UserRepository(s).get_many([], CID, viewer_id=uuid.uuid4()) == []
    assert await SettingsRepository(s).get_many([], CID) == []
    s.execute.assert_not_called()
