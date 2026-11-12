"""
@file test_plugin_key_repo.py
@brief Unit tests for PluginApiKeyRepository (session mocked).
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

from app.models.plugin import PluginApiKey
from app.repositories.plugin_key_repo import PluginApiKeyRepository

CID = uuid.uuid4()


def _repo(result: MagicMock | None = None) -> tuple[PluginApiKeyRepository, AsyncMock]:
    session = AsyncMock()
    session.add = MagicMock()
    if result is not None:
        session.execute.return_value = result
    return PluginApiKeyRepository(session), session


async def test_plugin_exists_true_and_scoped() -> None:
    repo, session = _repo(MagicMock(first=lambda: (1,)))
    assert await repo.plugin_exists("hello", CID) is True
    sql = str(session.execute.await_args.args[0])
    assert "plugins.community_id" in sql
    assert "plugins.deleted_at IS NULL" in sql


async def test_plugin_exists_false() -> None:
    repo, _ = _repo(MagicMock(first=lambda: None))
    assert await repo.plugin_exists("nope", CID) is False


async def test_create_adds_flushes_refreshes() -> None:
    repo, session = _repo()
    row = await repo.create(plugin_id="hello", community_id=CID, key_hash="h", key_hint="abcd")
    assert isinstance(row, PluginApiKey)
    assert (row.plugin_id, row.community_id, row.key_hash, row.key_hint) == (
        "hello",
        CID,
        "h",
        "abcd",
    )
    session.add.assert_called_once_with(row)
    session.flush.assert_awaited_once()
    session.refresh.assert_awaited_once_with(row)


async def test_list_for_plugin_scoped_newest_first() -> None:
    keys = [MagicMock(), MagicMock()]
    scalars = MagicMock(all=lambda: keys)
    repo, session = _repo(MagicMock(scalars=lambda: scalars))
    assert await repo.list_for_plugin("hello", CID) == keys
    sql = str(session.execute.await_args.args[0])
    assert "plugin_api_keys.community_id" in sql
    assert "ORDER BY plugin_api_keys.created_at DESC" in sql


async def test_get_scoped_to_plugin_and_community() -> None:
    found = MagicMock()
    repo, session = _repo(MagicMock(scalar_one_or_none=lambda: found))
    assert await repo.get(uuid.uuid4(), "hello", CID) is found
    sql = str(session.execute.await_args.args[0])
    assert "plugin_api_keys.plugin_id" in sql
    assert "plugin_api_keys.community_id" in sql


async def test_revoke_sets_timestamp_and_flushes() -> None:
    repo, session = _repo()
    key = MagicMock(spec=PluginApiKey)
    key.revoked_at = None
    out = await repo.revoke(key)
    assert out.revoked_at is not None
    session.flush.assert_awaited_once()


async def test_revoke_idempotent() -> None:
    repo, session = _repo()
    key = MagicMock(spec=PluginApiKey)
    key.revoked_at = "earlier"
    await repo.revoke(key)
    assert key.revoked_at == "earlier"
    session.flush.assert_not_awaited()
