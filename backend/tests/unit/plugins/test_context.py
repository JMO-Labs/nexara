"""@file Unit tests for PluginContext permission and isolation enforcement."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from sqlalchemy.dialects import postgresql

from app.plugins.context import NOTIFY_LIMIT_PER_MINUTE, PluginContext
from app.plugins.manifest import PluginManifest

COMMUNITY = uuid.uuid4()


def _manifest(perms: list[str]) -> PluginManifest:
    return PluginManifest.model_validate(
        {
            "id": "hello",
            "name": "Hello",
            "version": "1.0.0",
            "author": "a",
            "description": "d",
            "min_core_version": "0.1.0",
            "permissions": perms,
            "settings": {"greeting": {"type": "string", "label": "G"}},
        }
    )


def _ctx(
    perms: list[str], settings: dict | None = None, clock=None, community=COMMUNITY, session=None
) -> PluginContext:
    if session is None:
        session = AsyncMock()
        found = MagicMock()
        found.scalar_one_or_none.return_value = uuid.uuid4()
        session.execute.return_value = found
    return PluginContext(
        plugin_id="hello",
        manifest=_manifest(perms),
        session=session,
        community_id=community,
        storage_client=AsyncMock(),
        notification_service=AsyncMock(),
        settings=settings,
        clock=clock,
    )


def _sql(stmt) -> str:
    return str(
        stmt.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True})
    )


MSG = "Plugin 'hello' does not have permission '{}'"


class TestDb:
    async def test_read_requires_permission(self):
        with pytest.raises(PermissionError, match=MSG.format("db_read")):
            await _ctx([]).db.get("k")

    async def test_write_requires_permission(self):
        with pytest.raises(PermissionError, match=MSG.format("db_write")):
            await _ctx(["db_read"]).db.set("k", 1)

    async def test_get_queries_only_plugin_data_scoped(self):
        ctx = _ctx(["db_read"])
        result = MagicMock()
        result.scalar_one_or_none.return_value = {"a": 1}
        ctx._session.execute.return_value = result
        assert await ctx.db.get("k") == {"a": 1}
        sql = str(
            ctx._session.execute.call_args[0][0].compile(compile_kwargs={"literal_binds": True})
        )
        assert "plugin_data" in sql
        assert "'hello'" in sql and COMMUNITY.hex in sql
        assert "FROM plugin_data" in sql

    async def test_set_writes_scoped(self):
        ctx = _ctx(["db_write"])
        await ctx.db.set("k", {"x": 1})
        ctx._session.execute.assert_awaited_once()
        ctx._session.flush.assert_awaited()
        compiled = ctx._session.execute.call_args[0][0].compile(dialect=postgresql.dialect())
        assert str(compiled).startswith("INSERT INTO plugin_data")
        assert compiled.params["plugin_id"] == "hello"
        assert compiled.params["community_id"] == COMMUNITY
        assert compiled.params["key"] == "k"
        assert compiled.params["value_json"] == {"x": 1}

    async def test_delete_scoped(self):
        ctx = _ctx(["db_write"])
        await ctx.db.delete("k")
        ctx._session.flush.assert_awaited()
        sql = _sql(ctx._session.execute.call_args[0][0])
        assert "DELETE FROM plugin_data" in sql
        assert "'hello'" in sql and str(COMMUNITY) in sql and "'k'" in sql


class TestSettings:
    def test_get_default_and_saved(self):
        ctx = _ctx([], settings={"greeting": "hi"})
        assert ctx.settings.get("greeting") == "hi"
        assert ctx.settings.get("missing", 5) == 5

    def test_set_declared_only(self):
        ctx = _ctx([])
        ctx.settings.set("greeting", "yo")
        assert ctx.settings["greeting"] == "yo"
        with pytest.raises(KeyError):
            ctx.settings.set("undeclared", 1)


class TestStorage:
    async def test_requires_permission(self):
        with pytest.raises(PermissionError, match=MSG.format("storage_access")):
            await _ctx([]).storage.get("a.txt")

    async def test_namespaced(self):
        ctx = _ctx(["storage_access"])
        await ctx.storage.put("a.txt", b"x", "text/plain")
        ctx._storage.put.assert_awaited_with(f"plugins/hello/{COMMUNITY}/a.txt", b"x", "text/plain")

    async def test_communities_get_different_prefixes(self):
        other = uuid.uuid4()
        a, b = _ctx(["storage_access"]), _ctx(["storage_access"], community=other)
        await a.storage.put("a.txt", b"x", "t")
        await b.storage.put("a.txt", b"x", "t")
        ka = a._storage.put.await_args[0][0]
        kb = b._storage.put.await_args[0][0]
        assert ka != kb and str(other) in kb

    @pytest.mark.parametrize("key", ["../other/a", "/abs", "a/../../b", ""])
    async def test_rejects_escape(self, key):
        with pytest.raises(ValueError):
            await _ctx(["storage_access"]).storage.get(key)


class TestNotify:
    async def test_requires_permission(self):
        with pytest.raises(PermissionError, match=MSG.format("send_notifications")):
            await _ctx([]).notify(uuid.uuid4(), "plugin.x", {})

    async def test_delegates(self):
        ctx = _ctx(["send_notifications"])
        uid = uuid.uuid4()
        await ctx.notify(uid, "plugin.x", {"a": 1})
        ctx._notifications.notify.assert_awaited_once_with(uid, "plugin.x", {"a": 1}, actor_id=None)

    async def test_rate_limited(self):
        now = [1000.0]
        ctx = _ctx(["send_notifications"], clock=lambda: now[0], community=uuid.uuid4())
        for _ in range(NOTIFY_LIMIT_PER_MINUTE):
            await ctx.notify(uuid.uuid4(), "t", {})
        with pytest.raises(RuntimeError, match="rate limit"):
            await ctx.notify(uuid.uuid4(), "t", {})
        now[0] += 61
        await ctx.notify(uuid.uuid4(), "t", {})


    async def test_budget_shared_across_contexts(self):
        now = [1000.0]
        ctxs = [
            _ctx(["send_notifications"], clock=lambda: now[0], community=uuid.uuid4())
            for _ in range(2)
        ]
        # distinct communities keep distinct budgets; same community shares
        c1 = _ctx(["send_notifications"], clock=lambda: now[0], community=ctxs[0].community_id)
        for _ in range(NOTIFY_LIMIT_PER_MINUTE):
            await ctxs[0].notify(uuid.uuid4(), "t", {})
        with pytest.raises(RuntimeError, match="rate limit"):
            await c1.notify(uuid.uuid4(), "t", {})
        await ctxs[1].notify(uuid.uuid4(), "t", {})

    async def test_rejects_user_outside_community(self):
        session = AsyncMock()
        missing = MagicMock()
        missing.scalar_one_or_none.return_value = None
        session.execute.return_value = missing
        ctx = _ctx(["send_notifications"], session=session)
        with pytest.raises(PermissionError, match="community"):
            await ctx.notify(uuid.uuid4(), "t", {})
        ctx._notifications.notify.assert_not_awaited()


class TestHttp:
    def test_requires_permission(self):
        with pytest.raises(PermissionError, match=MSG.format("external_http")):
            _ctx([]).http_client()

    async def test_returns_client(self):
        async with _ctx(["external_http"]).http_client() as c:
            assert isinstance(c, httpx.AsyncClient)


def test_immutable():
    ctx = _ctx([])
    with pytest.raises(AttributeError):
        ctx.community_id = uuid.uuid4()
