"""
@file test_tree_service_pg.py
@brief Real-Postgres: the tree masks hidden people and household members,
       drops blocked users, and the group tree never returns outsiders.
"""

from __future__ import annotations

import os
import uuid
from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.models.community import Community
from app.models.household import HouseholdMember
from app.models.moderation import UserBlock
from app.models.relation import Relation
from app.models.subgroup import Subgroup, SubgroupMember
from app.models.user import User
from app.models.user_settings import UserSettings
from app.repositories.community_repo import CommunityRepository
from app.repositories.profile_repo import ProfileRepository
from app.repositories.relation_repo import RelationRepository
from app.repositories.tree_repo import TreeRepository
from app.services.tree_service import TreeService

TEST_DB_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://nexara:nexara@localhost:5432/nexara_test"
)


@pytest.fixture
async def session():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        async with sess.begin():
            yield sess
            await sess.rollback()
    await engine.dispose()


async def _cid(s: AsyncSession) -> uuid.UUID:
    c = Community(name=f"tree-{uuid.uuid4().hex[:6]}")
    s.add(c)
    await s.flush()
    return c.id


async def _user(s, cid, name, relations=None, **kw) -> User:
    sfx = uuid.uuid4().hex[:6]
    u = User(
        community_id=cid, email=f"{name}_{sfx}@nexara.dev", username=f"{name}_{sfx}",
        display_name=name, **kw,
    )  # fmt: skip
    s.add(u)
    await s.flush()
    vis = {"relations": relations} if relations else {}
    s.add(UserSettings(user_id=u.id, community_id=cid, field_visibility=vis))
    await s.flush()
    return u


async def _rel(s, cid, frm, kind, to=None, member=None) -> None:
    s.add(
        Relation(
            community_id=cid, from_user_id=frm.id, to_user_id=to.id if to else None,
            to_household_member_id=member.id if member else None, kind=kind,
            status="confirmed", created_by=frm.id,
        )
    )  # fmt: skip
    await s.flush()


def _svc(s, cid) -> TreeService:
    return TreeService(
        RelationRepository(s), TreeRepository(s), ProfileRepository(s), CommunityRepository(s), cid
    )


async def test_hidden_user_and_member_are_private_but_edges_stay(session) -> None:
    cid = await _cid(session)
    me = await _user(session, cid, "Me")
    mum = await _user(session, cid, "Mum", relations="private", birthday=date(1950, 1, 1))
    gran = await _user(session, cid, "Gran")
    await _rel(session, cid, mum, "parent", me)  # Mum is parent of Me
    await _rel(session, cid, me, "parent", gran)  # Me is parent of Gran?? (child test below)
    secret = HouseholdMember(
        community_id=cid, owner_id=gran.id, kind="person", name="Uncle Secret",
        visibility="private", birthday=date(1940, 2, 2),
    )  # fmt: skip
    session.add(secret)
    await session.flush()
    await _rel(session, cid, gran, "sibling", member=secret)
    tree = await _svc(session, cid).family(me, gens=5)
    dump = tree.model_dump_json()
    for leaked in ("Mum", "Uncle Secret", str(mum.id), str(secret.id), mum.username, "1950"):
        assert leaked not in dump
    private = [n for n in tree.nodes if n.kind == "private"]
    assert len(private) == 2
    assert all(n.name == "Private relative" and n.link is None for n in private)
    assert {n.id for n in private} == {"p:1", "p:2"}
    ids = {n.id for n in tree.nodes}
    assert all(e.a in ids and e.b in ids for e in tree.edges)
    assert len(tree.edges) == 3


async def test_blocked_user_and_edges_dropped(session) -> None:
    cid = await _cid(session)
    me = await _user(session, cid, "Me")
    ex = await _user(session, cid, "Blocked")
    kid = await _user(session, cid, "Kid")
    await _rel(session, cid, me, "parent", kid)
    await _rel(session, cid, ex, "parent", kid)
    session.add(UserBlock(community_id=cid, blocker_id=me.id, blocked_id=ex.id))
    await session.flush()
    tree = await _svc(session, cid).family(me)
    assert {n.name for n in tree.nodes} == {"Me", "Kid"}
    assert len(tree.edges) == 1


async def test_memorial_dates_only_when_birthday_shared(session) -> None:
    cid = await _cid(session)
    me = await _user(session, cid, "Me")
    from datetime import UTC, datetime

    kw = {"birthday": date(1930, 3, 4), "passed_on": date(2020, 1, 2)}
    kw["memorialized_at"] = datetime.now(UTC)  # type: ignore[assignment]
    shared = await _user(session, cid, "Shared", **kw)
    hidden = await _user(session, cid, "Hid", **kw)
    hidden_s = await ProfileRepository(session).get_settings(hidden.id)
    hidden_s.show_birthday_to = "nobody"
    await _rel(session, cid, shared, "parent", me)
    await _rel(session, cid, hidden, "parent", me)
    tree = await _svc(session, cid).family(me)
    by = {n.name: n for n in tree.nodes}
    assert by["Shared"].memorial and by["Shared"].born == "1930-03-04"
    assert by["Hid"].memorial and by["Hid"].born is None and by["Hid"].died is None


async def test_group_tree_excludes_outsiders(session) -> None:
    cid = await _cid(session)
    me = await _user(session, cid, "Me")
    sis = await _user(session, cid, "Sis")
    out1 = await _user(session, cid, "OutsiderOne")
    out2 = await _user(session, cid, "OutsiderTwo")
    cousin = await _user(session, cid, "Cousin")
    g = Subgroup(community_id=cid, name="G", slug=f"g-{uuid.uuid4().hex[:8]}", join_policy="open")
    session.add(g)
    await session.flush()
    for u in (me, sis, cousin):
        session.add(SubgroupMember(community_id=cid, subgroup_id=g.id, user_id=u.id))
    await session.flush()
    await _rel(session, cid, me, "sibling", sis)
    await _rel(session, cid, out1, "parent", me)
    await _rel(session, cid, out1, "parent", out2)
    await _rel(session, cid, out2, "parent", cousin)
    tree = await _svc(session, cid).group(me, g.slug)
    dump = tree.model_dump_json()
    assert "Outsider" not in dump and str(out1.id) not in dump and str(out2.id) not in dump
    assert {n.kind for n in tree.nodes} == {"user"}
    assert {n.name for n in tree.nodes} == {"Me", "Sis", "Cousin"}
    kinds = sorted(e.kind for e in tree.edges)
    assert kinds == ["sibling", "via_family"]
    via = next(e for e in tree.edges if e.kind == "via_family")
    assert {via.a, via.b} == {f"u:{me.id}", f"u:{cousin.id}"}


async def test_group_tree_requires_membership(session) -> None:
    from app.core.exceptions import NotFoundError

    cid = await _cid(session)
    me = await _user(session, cid, "Me")
    g = Subgroup(community_id=cid, name="G", slug=f"g-{uuid.uuid4().hex[:8]}", join_policy="open")
    session.add(g)
    await session.flush()
    with pytest.raises(NotFoundError):
        await _svc(session, cid).group(me, g.slug)
