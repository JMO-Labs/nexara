"""
@file test_signins_api.py
@brief Admin sign-in log (routes, CSV) and member session service against real Postgres.
"""

from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.core.dependencies import get_current_user, get_db
from app.core.deps_signins import get_admin_signin_service
from app.core.exceptions import AppError, NotFoundError
from app.core.security import hash_token
from app.models.auth import RefreshToken
from app.models.community import Community
from app.models.signin_event import SigninEvent
from app.models.user import User
from app.repositories.signin_repo import SigninRepository
from app.repositories.token_repo import TokenRepository
from app.services.admin_signin_service import AdminSigninService, csv_safe
from app.services.session_service import SessionService

DB = os.environ.get("DATABASE_URL", "postgresql+asyncpg://nexara:nexara@localhost:5432/nexara_test")
CHROME = "Mozilla/5.0 (X11; Linux x86_64) Chrome/120.0 Safari/537.36"


@pytest.fixture
async def session():
    engine = create_async_engine(DB)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        async with s.begin():
            yield s
            await s.rollback()
    await engine.dispose()


async def _user(s, cid, name):
    u = User(community_id=cid, email=f"{name}@x.dev", username=name, display_name=name)
    s.add(u)
    await s.flush()
    return u


@pytest.fixture
async def world(session):
    c = Community(name=f"si-{uuid.uuid4().hex[:6]}")
    session.add(c)
    await session.flush()
    n = uuid.uuid4().hex[:6]
    return c, await _user(session, c.id, f"a{n}"), await _user(session, c.id, f"b{n}")


async def _family(session, user, raw, ua=CHROME, ip="10.0.0.1", fam=None):
    fam = fam or uuid.uuid4()
    session.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(raw),
            family_id=fam,
            expires_at=datetime.now(UTC) + timedelta(days=1),
            ip_address=ip,
            user_agent=ua,
        )
    )
    await session.flush()
    return fam


async def test_sessions_list_marks_current_and_revoke_others(session, world):
    _, a, b = world
    f1 = await _family(session, a, "raw1")
    f2 = await _family(session, a, "raw2", ua="Mozilla/5.0 (iPhone) Safari/604")
    fb = await _family(session, b, "rawb")
    svc = SessionService(TokenRepository(session), a.id)
    rows = await svc.list("raw1")
    assert {r.family_id: r.current for r in rows} == {f1: True, f2: False}
    assert {r.device for r in rows} == {"Chrome on Linux", "Safari on iOS"}
    await svc.revoke_others("raw1")
    assert [r.family_id for r in await svc.list("raw1")] == [f1]
    # other user's family untouched
    assert [
        r.family_id for r in await SessionService(TokenRepository(session), b.id).list(None)
    ] == [fb]


async def test_revoke_foreign_family_is_404_and_own_stops_refresh(session, world):
    _, a, b = world
    fb = await _family(session, b, "rawb")
    fa = await _family(session, a, "rawa")
    svc = SessionService(TokenRepository(session), a.id)
    with pytest.raises(NotFoundError):
        await svc.revoke(fb)
    await svc.revoke(fa)
    tok = await TokenRepository(session).find_by_hash(hash_token("rawa"))
    assert tok.revoked_at is not None
    with pytest.raises(NotFoundError):
        await svc.revoke(fa)


async def test_signin_search_filters_and_cursor(session, world):
    c, a, _ = world
    now = datetime.now(UTC)
    for i in range(5):
        session.add(
            SigninEvent(
                community_id=c.id,
                user_id=a.id if i % 2 == 0 else None,
                email_tried=f"who{i}@x.dev",
                method="password",
                success=i % 2 == 0,
                ip="192.168.1.5",
                device="Chrome on Linux",
                created_at=now - timedelta(minutes=i),
            )
        )
    await session.flush()
    svc = AdminSigninService(
        SigninRepository(session), c.id, MagicMock(), a.id, None, AsyncMock(), None
    )
    kw = dict(q=None, success=None, method=None, since=None)
    p1 = await svc.list(**kw, cursor=None, limit=2)
    assert len(p1.items) == 2 and p1.next_cursor
    p2 = await svc.list(**kw, cursor=p1.next_cursor, limit=10)
    assert len(p2.items) == 3 and p2.next_cursor is None
    assert p1.items[0].user == a.username
    assert len((await svc.list(**{**kw, "success": False}, cursor=None)).items) == 2
    assert len((await svc.list(**{**kw, "q": "192.168"}, cursor=None)).items) == 5
    assert len((await svc.list(**{**kw, "q": "who3"}, cursor=None)).items) == 1
    assert len((await svc.list(**{**kw, "q": "100%"}, cursor=None)).items) == 0


def test_csv_safe_prefixes_formulas():
    assert csv_safe("=1+1") == "'=1+1"
    assert csv_safe("-2") == "'-2"
    assert csv_safe("@a") == "'@a"
    assert csv_safe("+1") == "'+1"
    assert csv_safe(" =1") == "' =1"
    assert csv_safe("\n=1") == "'\n=1"
    assert csv_safe(None) == "" and csv_safe("ok") == "ok"


def _client(test_app, role, svc=None):
    user = SimpleNamespace(id=uuid.uuid4(), role=role, community_id=uuid.uuid4())
    test_app.dependency_overrides[get_current_user] = lambda: user
    if svc:
        test_app.dependency_overrides[get_admin_signin_service] = lambda: svc
    return AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test")


async def test_csv_route_header_injection_and_audit(test_app, monkeypatch):
    ev = SimpleNamespace(
        id=uuid.uuid4(),
        created_at=datetime(2026, 1, 2, tzinfo=UTC),
        email_tried="=cmd@x.dev",
        method="password",
        success=False,
        reason="bad_password",
        ip="1.2.3.4",
        device="Chrome on Linux",
    )
    calls = []

    async def fake_search(self, cid, **kw):
        calls.append(kw)
        return [(ev, None)] if len(calls) == 1 else []

    monkeypatch.setattr(SigninRepository, "search", fake_search)

    @asynccontextmanager
    async def reader():
        yield MagicMock()

    audit = MagicMock()
    audit.append = AsyncMock()
    svc = AdminSigninService(
        None, uuid.uuid4(), audit, uuid.uuid4(), "9.9.9.9", AsyncMock(), reader
    )
    async with _client(test_app, "admin", svc) as c:
        r = await c.get("/api/v1/admin/signins.csv?success=false")
    test_app.dependency_overrides.clear()
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    lines = r.text.splitlines()
    assert lines[0] == "time,email,user,method,success,reason,ip,device"
    assert lines[1].split(",")[1] == "'=cmd@x.dev"
    assert audit.append.await_args.kwargs["action"] == "signins.exported"


async def test_signin_routes_forbid_members(test_app):
    async with _client(test_app, "member") as c:
        assert (await c.get("/api/v1/admin/signins")).status_code == 403
        assert (await c.get("/api/v1/admin/signins.csv")).status_code == 403
    test_app.dependency_overrides.clear()


async def test_sessions_http_cookie_marks_current_and_keeps_family(test_app, session, world):
    _, a, _ = world
    f1 = await _family(session, a, "raw1")
    f2 = await _family(session, a, "raw2")
    user = SimpleNamespace(id=a.id, role="member", community_id=a.community_id)

    async def _db():
        yield session

    test_app.dependency_overrides[get_current_user] = lambda: user
    test_app.dependency_overrides[get_db] = _db
    base = "/api/v1/auth/sessions"
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as c:
        c.cookies.set("refresh_token", "raw1")
        r = await c.get(base)
        assert {x["family_id"]: x["current"] for x in r.json()} == {str(f1): True, str(f2): False}
        assert (await c.post(f"{base}/revoke-others")).status_code == 200
        assert [x["family_id"] for x in (await c.get(base)).json()] == [str(f1)]
        c.cookies.set("refresh_token", "unknown")
        r = await c.post(f"{base}/revoke-others")
        assert r.status_code == 400 and r.json()["error"]["code"] == "NO_CURRENT_SESSION"
        assert (await c.delete(f"{base}/{uuid.uuid4()}")).status_code == 404
    test_app.dependency_overrides.clear()
    assert [
        r.family_id for r in await SessionService(TokenRepository(session), a.id).list("raw1")
    ] == [f1]


async def test_revoke_others_rejects_revoked_or_missing_cookie(session, world):
    _, a, _ = world
    await _family(session, a, "raw1")
    await _family(session, a, "raw2")
    svc = SessionService(TokenRepository(session), a.id)
    await svc.revoke((await svc.list("raw1"))[0].family_id)
    for raw in (None, "nope"):
        with pytest.raises(AppError) as e:
            await svc.revoke_others(raw)
        assert e.value.code == "NO_CURRENT_SESSION"
    assert len(await svc.list(None)) == 1  # nothing else was revoked
    revoked = (await TokenRepository(session).list_active_families(a.id))[0]
    await svc.revoke(revoked.family_id)
    with pytest.raises(AppError):  # a dead cookie is no current session
        await svc.revoke_others("raw1")
