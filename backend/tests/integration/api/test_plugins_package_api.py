"""
@file test_plugins_package_api.py
@brief Package install via a mocked plugin host, against the real app and real Postgres.
"""

from __future__ import annotations

import json
import os
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.core.config import Settings, get_settings
from app.core.dependencies import get_current_user, get_db
from app.models.plugin import PluginCommunity, PluginInstall, PluginToken
from app.models.user import COMMUNITY_DEFAULT, User
from app.plugins.manifest import parse_manifest
from app.services.plugin_host_client import PluginHostClient

DB_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://nexara:nexara@localhost:5432/nexara_test"
)
CID = uuid.UUID(COMMUNITY_DEFAULT)
HOST = "http://plugin-host:8700"
SHA = "c" * 64


def _manifest(pid: str):
    return parse_manifest(f"""
[plugin]
id = "{pid}"
name = "Echo"
version = "1.0.0"
runtime = "node"
entrypoint = "index.js"
[bot]
display_name = "Echo Bot"
username = "echo"
[permissions]
scopes = ["posts:read"]
[settings.api_key]
type = "secret"
label = "Key"
""")


@pytest.fixture
async def session():
    engine = create_async_engine(DB_URL)
    async with async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)() as s:
        async with s.begin():
            yield s
            await s.rollback()
    await engine.dispose()


@pytest.fixture(autouse=True)
def _no_pubsub():
    with patch("app.services.realtime.event_bus.EventBus.emit", AsyncMock()):
        yield


@pytest.fixture
async def env(test_app, session):
    calls: list[httpx.Request] = []
    state = {"down": False}

    def handler(req: httpx.Request) -> httpx.Response:
        if state["down"]:
            raise httpx.ConnectError("refused", request=req)
        calls.append(req)
        if req.method == "GET" and req.url.path.endswith("/logs"):
            return httpx.Response(200, json={"lines": ["[p] ready"]})
        return httpx.Response(204 if req.method in ("DELETE", "POST") else 202)

    async def _db():  # savepoint per request, rolled back on error like get_db
        sp = await session.begin_nested()
        try:
            yield session
            await sp.commit()
        except Exception:
            await sp.rollback()
            raise

    n = uuid.uuid4().hex[:8]
    owner = User(
        community_id=CID,
        email=f"pk_{n}@nexara.dev",
        username=f"pk_{n}",
        display_name=n,
        role="admin",
    )
    session.add(owner)
    await session.flush()
    settings = Settings(**{**get_settings().model_dump(), "PLUGIN_HOST_URL": HOST})
    test_app.dependency_overrides[get_db] = _db
    test_app.dependency_overrides[get_current_user] = lambda: owner
    test_app.dependency_overrides[get_settings] = lambda: settings
    pid = f"dev.pkg.{n}"
    client = PluginHostClient(HOST, "hs", httpx.MockTransport(handler))
    with (
        patch.object(PluginHostClient, "from_settings", return_value=client),
        patch(
            "app.services.plugin_host_ops.fetch_package_manifest",
            AsyncMock(return_value=_manifest(pid)),
        ),
    ):
        async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://t") as c:
            yield SimpleNamespace(c=c, s=session, pid=pid, calls=calls, state=state)
    test_app.dependency_overrides.clear()


async def _install(e):
    return await e.c.post(
        "/api/v1/plugins/install",
        json={
            "source": "package",
            "package_url": "https://x.test/p.tgz",
            "sha256": SHA,
            "approved_scopes": ["posts:read"],
        },
    )


async def _row(e):
    return (
        await e.s.execute(select(PluginInstall).where(PluginInstall.plugin_id == e.pid))
    ).scalar_one_or_none()


async def _enable(e, on: bool = True):
    return await e.c.patch(f"/api/v1/plugins/{e.pid}/communities/{CID}", json={"enabled": on})


async def _active_tokens(e, inst) -> int:
    rows = await e.s.execute(
        select(PluginToken).where(
            PluginToken.install_id == inst.id, PluginToken.revoked_at.is_(None)
        )
    )
    return len(list(rows.scalars()))


async def test_install_records_only_then_first_enable_pushes(env):
    r = await _install(env)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "disabled" and body["source"] == "package" and not body["enabled"]
    inst = await _row(env)
    assert inst.endpoint_url == f"{HOST}/plugins/{env.pid}/events" and inst.sha256 == SHA
    assert env.calls == []  # host untouched until enable
    r = await _enable(env)
    assert r.status_code == 200, r.text
    assert r.json()["credentials"] is None
    pc = await env.s.get(PluginCommunity, (inst.id, CID))
    assert pc.enabled and pc.bot_user_id is not None
    put = env.calls[-1]
    assert put.method == "PUT" and put.url.path == f"/plugins/{env.pid}"
    pushed = json.loads(put.content)
    assert pushed["env"]["NEXARA_COMMUNITIES"][0]["bot_user_id"] == str(pc.bot_user_id)
    assert await _active_tokens(env, inst) == 1 and inst.status == "installing"
    r = await env.c.get(f"/api/v1/plugins/{env.pid}/logs")
    assert r.json() == {"lines": ["[p] ready"]}


async def test_host_down_enable_503_nothing_enabled(env):
    assert (await _install(env)).status_code == 201
    env.state["down"] = True
    r = await _enable(env)
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "plugin_host_unavailable"
    inst = await _row(env)
    assert await env.s.get(PluginCommunity, (inst.id, CID)) is None
    assert await _active_tokens(env, inst) == 0


async def test_host_down_disable_still_revokes(env):
    assert (await _install(env)).status_code == 201
    assert (await _enable(env)).status_code == 200
    env.state["down"] = True
    r = await _enable(env, False)
    assert r.status_code == 200, r.text
    assert r.json()["enabled"] is False and r.json()["host_error"] == "unreachable"
    inst = await _row(env)
    pc = await env.s.get(PluginCommunity, (inst.id, CID))
    bot = await env.s.get(User, pc.bot_user_id)
    assert not pc.enabled and not bot.is_active and inst.status == "disabled"
    assert await _active_tokens(env, inst) == 0


async def test_uninstall_deletes_on_host(env):
    assert (await _install(env)).status_code == 201
    assert (await _enable(env)).status_code == 200
    r = await env.c.request("DELETE", f"/api/v1/plugins/{env.pid}", json={"delete_content": False})
    assert r.status_code == 204
    assert env.calls[-1].method == "DELETE" and env.calls[-1].url.params["purge"] == "false"
    assert await _row(env) is None


async def test_uninstall_host_down_removes_and_reports(env):
    assert (await _install(env)).status_code == 201
    assert (await _enable(env)).status_code == 200
    env.state["down"] = True
    r = await env.c.request("DELETE", f"/api/v1/plugins/{env.pid}")
    assert r.status_code == 200
    assert r.json() == {"removed": True, "host_error": "unreachable"}
    assert await _row(env) is None
