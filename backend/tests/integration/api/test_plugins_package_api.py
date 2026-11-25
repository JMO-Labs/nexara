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
            "app.services.plugin_service.fetch_package_manifest",
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


async def test_package_install_pushes_and_enables(env):
    r = await _install(env)
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "installing" and r.json()["source"] == "package"
    inst = await _row(env)
    assert inst.endpoint_url == f"{HOST}/plugins/{env.pid}/events" and inst.sha256 == SHA
    pc = (
        await env.s.execute(select(PluginCommunity).where(PluginCommunity.install_id == inst.id))
    ).scalar_one()
    assert pc.enabled and pc.bot_user_id is not None
    put = env.calls[-1]
    assert put.method == "PUT" and put.url.path == f"/plugins/{env.pid}"
    body = json.loads(put.content)
    assert body["env"]["NEXARA_COMMUNITIES"][0]["bot_user_id"] == str(pc.bot_user_id)
    active = (
        await env.s.execute(
            select(PluginToken).where(
                PluginToken.install_id == inst.id, PluginToken.revoked_at.is_(None)
            )
        )
    ).scalars()
    assert len(list(active)) == 1
    r = await env.c.get(f"/api/v1/plugins/{env.pid}/logs")
    assert r.json() == {"lines": ["[p] ready"]}


async def test_host_down_install_503_nothing_persisted(env):
    env.state["down"] = True
    r = await _install(env)
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "plugin_host_unavailable"
    assert await _row(env) is None


async def test_host_down_disable_503_status_unchanged(env):
    assert (await _install(env)).status_code == 201
    env.state["down"] = True
    r = await env.c.patch(f"/api/v1/plugins/{env.pid}/communities/{CID}", json={"enabled": False})
    assert r.status_code == 503
    inst = await _row(env)
    pc = await env.s.get(PluginCommunity, (inst.id, CID))
    assert pc.enabled and inst.status == "installing"


async def test_uninstall_deletes_on_host(env):
    assert (await _install(env)).status_code == 201
    r = await env.c.request("DELETE", f"/api/v1/plugins/{env.pid}", json={"delete_content": False})
    assert r.status_code == 204
    assert env.calls[-1].method == "DELETE" and env.calls[-1].url.params["purge"] == "false"
    assert await _row(env) is None
