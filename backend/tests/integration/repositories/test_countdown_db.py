"""
@file test_countdown_db.py
@brief Real-Postgres tests: countdown visibility, follow, delete, Home list.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.core.exceptions import AuthorizationError, NotFoundError
from app.models.post import Post
from app.models.subgroup import Subgroup, SubgroupMember
from app.models.user import User
from app.repositories.countdown_repo import CountdownRepository
from app.schemas.countdown import CountdownCreate
from app.services.countdown_service import CountdownService

URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://nexara:nexara@localhost:5432/nexara_test"
)
CID = uuid.UUID("00000000-0000-0000-0000-000000000001")


@pytest.fixture
async def session():
    engine = create_async_engine(URL)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        async with sess.begin():
            yield sess
            await sess.rollback()
    await engine.dispose()


async def _user(s: AsyncSession, role: str = "member") -> User:
    t = uuid.uuid4().hex[:8]
    u = User(community_id=CID, email=f"cd_{t}@nexara.dev", username=f"cd_{t}", display_name="c")
    u.role = role
    s.add(u)
    await s.flush()
    return u


def _svc(s: AsyncSession) -> CountdownService:
    return CountdownService(CountdownRepository(s), CID)


def _today() -> date:
    return datetime.now(UTC).date()


async def test_private_is_404_for_others_and_follow_requires_visibility(session):
    a, b = await _user(session), await _user(session)
    svc = _svc(session)
    r = await svc.create(a, CountdownCreate(title="x", target_date=_today(), visibility="private"))
    assert (await svc.get(a, r.id)).following is True
    with pytest.raises(NotFoundError):
        await svc.get(b, r.id)
    with pytest.raises(NotFoundError):
        await svc.follow(b, r.id, True)


async def test_subgroup_only_for_members(session):
    a, b = await _user(session), await _user(session)
    sg = Subgroup(community_id=CID, name="g", slug=f"g-{uuid.uuid4().hex[:8]}", created_by=a.id)
    session.add(sg)
    await session.flush()
    session.add(SubgroupMember(subgroup_id=sg.id, user_id=a.id))
    await session.flush()
    svc = _svc(session)
    body = CountdownCreate(
        title="x", target_date=_today(), visibility="subgroup", subgroup_id=sg.id
    )
    with pytest.raises(AuthorizationError):
        await svc.create(b, body)
    r = await svc.create(a, body)
    with pytest.raises(NotFoundError):
        await svc.get(b, r.id)
    session.add(SubgroupMember(subgroup_id=sg.id, user_id=b.id))
    await session.flush()
    assert (await svc.get(b, r.id)).id == r.id


async def test_delete_removes_feed_post_and_admin_may_delete(session):
    a, admin, other = await _user(session), await _user(session, "admin"), await _user(session)
    svc = _svc(session)
    r = await svc.create(a, CountdownCreate(title="x", target_date=_today()))
    post = (await session.execute(select(Post).where(Post.id == r.post_id))).scalar_one()
    assert post.countdown_id == r.id and post.visibility == "community"
    with pytest.raises(AuthorizationError):
        await svc.delete(other, r.id)
    await svc.delete(admin, r.id)
    await session.refresh(post)
    assert post.deleted_at is not None
    with pytest.raises(NotFoundError):
        await svc.get(a, r.id)


async def test_home_list_hides_old_oneoff_keeps_rolled_yearly(session):
    a = await _user(session)
    svc = _svc(session)
    old = _today() - timedelta(days=4)
    await svc.create(a, CountdownCreate(title="old", target_date=old))
    await svc.create(a, CountdownCreate(title="yearly", target_date=old, repeat_yearly=True))
    await svc.create(a, CountdownCreate(title="soon", target_date=_today() + timedelta(days=2)))
    titles = [r.title for r in await svc.list_following(a, False)]
    assert titles == ["soon", "yearly"]
    assert len(await svc.list_following(a, True)) == 3
    assert len(await svc.list_all(a)) == 3
