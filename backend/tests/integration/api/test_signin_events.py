"""
@file test_signin_events.py
@brief Real-Postgres tests: signin_events recording, queries, purge and PREF_MAP.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.models.signin_event import SigninEvent
from app.models.user import User
from app.repositories.signin_repo import SigninRepository
from app.services.auth.signin_log import record_signin
from app.services.notification_service import PREF_MAP

DB_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://nexara:nexara@localhost:5432/nexara_test"
)
CID = uuid.UUID("00000000-0000-0000-0000-000000000001")
UA = "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Firefox/121.0"


@pytest.fixture
async def session():
    """@brief Transactional session rolled back after each test."""
    engine = create_async_engine(DB_URL, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        async with sess.begin():
            yield sess
            await sess.rollback()
    await engine.dispose()


async def _user(session: AsyncSession) -> User:
    tag = uuid.uuid4().hex[:8]
    u = User(community_id=CID, email=f"si_{tag}@nexara.dev", username=f"si_{tag}", display_name="s")
    session.add(u)
    await session.flush()
    return u


def _req(ip: str = "198.51.100.7", ua: str = UA):
    return SimpleNamespace(client=SimpleNamespace(host=ip), headers={"user-agent": ua})


async def _rec(session, user, *, success=True, ip="198.51.100.7", notifier=None, **kw):
    return await record_signin(
        session,
        community_id=CID,
        user_id=user.id if user else None,
        email=kw.pop("email", "X@Y.com"),
        method="password",
        success=success,
        reason=None if success else "bad_password",
        request=_req(ip),
        notifier=notifier or SimpleNamespace(notify=AsyncMock()),
        **kw,
    )


def test_new_signin_in_pref_map():
    assert PREF_MAP["new_signin"] == ("notif_system_inapp", "notif_system_email")


async def test_record_persists_row_without_password(session):
    ev = await _rec(session, None, success=False)
    assert ev.id is not None
    assert str(ev.ip) == "198.51.100.7"
    assert ev.device == "Firefox on Linux"
    assert ev.email_tried == "x@y.com"
    assert ev.user_id is None
    assert "password" not in {c.name for c in SigninEvent.__table__.columns}


async def test_count_failures_and_window(session):
    repo = SigninRepository(session)
    for _ in range(3):
        await _rec(session, None, success=False)
    await _rec(session, None, success=True, ip="198.51.100.7")
    await _rec(session, None, success=False, ip="198.51.100.8")
    assert await repo.count_failures(CID, "198.51.100.7", 10) == 3
    await session.execute(
        update(SigninEvent).values(created_at=datetime.now(UTC) - timedelta(minutes=30))
    )
    assert await repo.count_failures(CID, "198.51.100.7", 10) == 0


async def test_second_login_same_device_no_alert(session):
    user = await _user(session)
    n1 = SimpleNamespace(notify=AsyncMock())
    await _rec(session, user, notifier=n1)  # first ever: no alert
    n1.notify.assert_not_awaited()
    n2 = SimpleNamespace(notify=AsyncMock())
    await _rec(session, user, notifier=n2)  # same device
    n2.notify.assert_not_awaited()


async def test_new_device_alerts(session):
    user = await _user(session)
    await _rec(session, user)
    n = SimpleNamespace(notify=AsyncMock())
    await record_signin(
        session,
        community_id=CID,
        user_id=user.id,
        email=user.email,
        method="sso",
        success=True,
        reason=None,
        request=_req(ua="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) Safari/604.1"),
        notifier=n,
    )
    n.notify.assert_awaited_once()
    assert n.notify.await_args.args[2]["device"] == "Safari on iOS"


async def test_purge_older_than_90_days(session):
    old = await _rec(session, None, success=False)
    await _rec(session, None, success=False)
    await session.execute(
        update(SigninEvent)
        .where(SigninEvent.id == old.id)
        .values(created_at=datetime.now(UTC) - timedelta(days=91))
    )
    assert await SigninRepository(session).purge_older_than(90) >= 1
    assert await SigninRepository(session).count_failures(CID, "198.51.100.7", 10) == 1
