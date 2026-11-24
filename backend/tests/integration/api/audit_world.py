"""
@file audit_world.py
@brief Shared real-DB fixture for the audit coverage tests (rolled-back transaction).
"""

from __future__ import annotations

import os
import uuid
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

import app.models  # noqa: F401
from app.core.config import Settings, get_settings
from app.core.dependencies import get_current_user, get_db
from app.core.deps_mail import get_google_mail_service
from app.core.security import hash_password
from app.models.audit import AuditLog
from app.models.community import Community
from app.models.user import User
from app.repositories.audit_repo import AuditRepository
from app.repositories.community_repo import CommunityRepository
from app.repositories.user_repo import UserRepository
from app.services.admin_google_mail import GoogleMailService

DB = os.environ.get("DATABASE_URL", "postgresql+asyncpg://nexara:nexara@localhost:5432/nexara_test")
CID = uuid.UUID("00000000-0000-0000-0000-000000000001")
PW = "correct horse battery"
S = Settings(
    SECRET_KEY="audit-cov-secret",
    JWT_ALGORITHM="HS256",
    APP_BASE_URL="https://home.example:8443",
    GOOGLE_MAIL_CLIENT_ID="cid",
    GOOGLE_MAIL_CLIENT_SECRET="csecret",
    ENABLE_METRICS=False,
)


class FakeValkey:
    """@brief set/getdel/delete stand-in."""

    def __init__(self) -> None:
        self.d: dict[str, str] = {}

    async def set(self, k, v, ex=None, nx=False):
        self.d[k] = v
        return True

    async def getdel(self, k):
        return self.d.pop(k, None)

    async def delete(self, *k):
        for x in k:
            self.d.pop(x, None)


@pytest.fixture
async def world(test_app):
    engine = create_async_engine(DB)
    async with engine.connect() as conn:
        trans = await conn.begin()
        s = AsyncSession(
            bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False
        )
        if await s.get(Community, CID) is None:
            s.add(Community(id=CID, name="Nexara"))
            await s.flush()
        users = []
        for role in ("admin", "member"):
            n = uuid.uuid4().hex[:8]
            u = User(
                community_id=CID,
                email=f"{role}{n}@x.dev",
                username=f"{role}{n}",
                display_name=f"{role.title()} {n}",
                role=role,
                password_hash=hash_password(PW),
            )
            s.add(u)
            users.append(u)
        await s.flush()
        admin, member = users
        cur = {"u": admin}

        async def get_db_override():
            yield s

        async def current():
            await s.refresh(cur["u"])
            return cur["u"]

        test_app.dependency_overrides[get_db] = get_db_override
        test_app.dependency_overrides[get_current_user] = current
        test_app.dependency_overrides[get_settings] = lambda: S
        vk = FakeValkey()
        test_app.dependency_overrides[get_google_mail_service] = lambda: GoogleMailService(
            CommunityRepository(s), UserRepository(s), S, vk, AuditRepository(s)
        )

        def client(as_user=None):
            cur["u"] = as_user or admin
            return AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test")

        async def rows(action: str) -> list[AuditLog]:
            res = await s.execute(
                select(AuditLog).where(
                    AuditLog.action == action,
                    (AuditLog.actor_id.in_([admin.id, member.id]))
                    | (AuditLog.target_id.in_([admin.id, member.id, CID])),
                )
            )
            return list(res.scalars())

        yield SimpleNamespace(
            s=s, admin=admin, member=member, client=client, rows=rows, app=test_app, vk=vk
        )
        test_app.dependency_overrides.clear()
        await s.close()
        await trans.rollback()
    await engine.dispose()


async def one(w, action, *, actor, target_id, target_type=None):
    """@brief Assert exactly one row for ``action`` with the given actor and target."""
    got = await w.rows(action)
    assert len(got) == 1, f"{action}: expected 1 row, got {len(got)}"
    r = got[0]
    assert r.actor_id == actor
    assert r.target_id == target_id and r.target_type
    if target_type:
        assert r.target_type == target_type
    return r
