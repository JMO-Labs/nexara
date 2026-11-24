"""
@file test_plugins_api.py
@brief Plugin admin, prefs and post-flag APIs against the real app and real Postgres.
"""

from __future__ import annotations

import os
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.core.dependencies import get_current_user, get_db
from app.models.community import Community
from app.models.post import Post
from app.models.user import COMMUNITY_DEFAULT, User

DB_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://nexara:nexara@localhost:5432/nexara_test"
)
CID = uuid.UUID(COMMUNITY_DEFAULT)


def _toml(pid: str) -> str:
    return f"""
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
events = ["post.created"]
[settings.api_key]
type = "secret"
label = "Key"
[user_prefs.notify]
type = "boolean"
label = "Notify me"
[composer_flags.silent]
type = "boolean"
label = "Silent"
"""


@pytest.fixture
async def session():
    """@brief One rolled-back transaction shared by the app and the test."""
    engine = create_async_engine(DB_URL)
    async with async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)() as s:
        async with s.begin():
            yield s
            await s.rollback()
    await engine.dispose()


async def _user(s: AsyncSession, role: str, cid: uuid.UUID = CID) -> User:
    n = uuid.uuid4().hex[:8]
    u = User(
        community_id=cid, email=f"p_{n}@nexara.dev", username=f"p_{n}", display_name=n, role=role
    )
    s.add(u)
    await s.flush()
    return u


@pytest.fixture
async def env(test_app, session):
    who: dict[str, User] = {}

    async def _db():
        yield session

    test_app.dependency_overrides[get_db] = _db
    test_app.dependency_overrides[get_current_user] = lambda: who["u"]
    other = Community(name=f"o-{uuid.uuid4().hex[:6]}")
    session.add(other)
    await session.flush()
    users = SimpleNamespace(
        owner=await _user(session, "admin"),
        member=await _user(session, "member"),
        other_admin=await _user(session, "admin", other.id),
    )
    pid = f"dev.test.{uuid.uuid4().hex[:8]}"
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://t") as c:
        yield SimpleNamespace(c=c, who=who, u=users, pid=pid, app=test_app, s=session)
    test_app.dependency_overrides.clear()


async def _install(e):
    e.who["u"] = e.u.owner
    with patch(
        "app.services.plugin_service.fetch_manifest_text", AsyncMock(return_value=_toml(e.pid))
    ):
        return await e.c.post(
            "/api/v1/plugins/install",
            json={
                "source": "url",
                "manifest_url": "https://x.test/m.toml",
                "endpoint_url": "http://echo:3000",
                "approved_scopes": ["posts:read"],
            },
        )


async def _enable(e):
    return await e.c.patch(
        f"/api/v1/plugins/{e.pid}/communities/{CID}",
        json={"enabled": True, "settings": {"api_key": "sekret"}},
    )


async def test_member_cannot_install(env):
    env.who["u"] = env.u.member
    r = await env.c.post("/api/v1/plugins/install", json={"source": "package"})
    assert r.status_code == 403


async def test_other_community_admin_cannot_install(env):
    env.who["u"] = env.u.other_admin
    r = await env.c.post("/api/v1/plugins/install", json={"source": "package"})
    assert r.status_code == 403


async def test_install_enable_credentials_and_masked_settings(env):
    r = await _install(env)
    assert r.status_code == 201, r.text
    r = await _enable(env)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["enabled"] and body["credentials"]["token"].startswith("nxp_")
    assert body["settings"]["api_key"] == {"set": True}
    r = await env.c.get(f"/api/v1/plugins/{env.pid}/settings")
    assert r.json()["api_key"] == {"set": True} and "sekret" not in r.text
    r = await env.c.get("/api/v1/plugins")
    assert any(p["plugin_id"] == env.pid and p["enabled"] for p in r.json())
    r = await env.c.request("DELETE", f"/api/v1/plugins/{env.pid}", json={"delete_content": True})
    assert r.status_code == 204


async def test_admin_cannot_manage_other_community(env):
    await _install(env)
    env.who["u"] = env.u.other_admin
    r = await env.c.patch(f"/api/v1/plugins/{env.pid}/communities/{CID}", json={"enabled": True})
    assert r.status_code == 403


async def test_member_ui_and_prefs_roundtrip(env):
    await _install(env)
    await _enable(env)
    env.who["u"] = env.u.member
    ui = (await env.c.get("/api/v1/plugins/ui")).json()
    assert ui[0]["plugin_id"] == env.pid and "silent" in ui[0]["composer_flags"]
    url = f"/api/v1/me/plugin-prefs/{env.pid}"
    assert (await env.c.get(url)).json() == {"notify": False}
    r = await env.c.put(url, json={"values": {"notify": True}})
    assert r.json() == {"notify": True}
    assert (await env.c.get(url)).json() == {"notify": True}
    assert (await env.c.put(url, json={"values": {"nope": 1}})).status_code == 422


async def test_post_flags_valid_stored_unknown_422(env):
    await _install(env)
    await _enable(env)
    env.who["u"] = env.u.member
    ok = await env.c.post(
        "/api/v1/posts", json={"content": "hi", "plugin_flags": {env.pid: {"silent": True}}}
    )
    assert ok.status_code == 201, ok.text
    stored = (
        await env.s.execute(select(Post.plugin_flags).where(Post.id == uuid.UUID(ok.json()["id"])))
    ).scalar_one()
    assert stored == {env.pid: {"silent": True}}
    for flags in ({"no.such": {"silent": True}}, {env.pid: {"bogus": True}}):
        r = await env.c.post("/api/v1/posts", json={"content": "x", "plugin_flags": flags})
        assert r.status_code == 422
        assert r.json()["error"]["code"] == "invalid_plugin_flag"


async def test_user_out_has_is_bot(env):
    env.who["u"] = env.u.member
    r = await env.c.get("/api/v1/users")
    assert r.status_code == 200
    assert all(u["is_bot"] is False for u in r.json()["items"])


async def test_plugin_token_cannot_reach_admin_or_prefs(env):
    await _install(env)
    r = await _enable(env)
    tok = r.json()["credentials"]["token"]
    env.app.dependency_overrides.pop(get_current_user)
    for method, path in (
        ("GET", "/api/v1/plugins"),
        ("POST", "/api/v1/plugins/install"),
        ("GET", "/api/v1/plugins/ui"),
        ("GET", f"/api/v1/plugins/{env.pid}/settings"),
        ("PATCH", f"/api/v1/plugins/{env.pid}/communities/{CID}"),
        ("DELETE", f"/api/v1/plugins/{env.pid}"),
        ("GET", f"/api/v1/me/plugin-prefs/{env.pid}"),
        ("PUT", f"/api/v1/me/plugin-prefs/{env.pid}"),
    ):
        r = await env.c.request(method, path, headers={"Authorization": f"Bearer {tok}"}, json={})
        assert r.status_code == 403, (method, path, r.text)
        assert r.json()["error"]["code"] == "plugin_scope_denied"
