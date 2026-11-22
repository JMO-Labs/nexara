"""
@file test_recipe_repo.py
@brief Real-Postgres: recipe search, visibility, soft-delete unlink and
       story @mention tagging.
"""

from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.models.list import List, ListItem
from app.models.subgroup import Subgroup, SubgroupMember
from app.models.tag import Tag
from app.models.user import User
from app.repositories.community_repo import CommunityRepository
from app.repositories.recipe_repo import RecipeRepository
from app.repositories.tag_repo import TagRepository
from app.schemas.recipe import RecipeCreate
from app.services.mention_tags import MentionTagsService
from app.services.recipe_service import RecipeService

TEST_DB_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://nexara:nexara@localhost:5432/nexara_test"
)
CID = uuid.UUID("00000000-0000-0000-0000-000000000001")


@pytest.fixture
async def session():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        async with sess.begin():
            yield sess
            await sess.rollback()
    await engine.dispose()


async def _user(s: AsyncSession, name: str) -> User:
    sfx = uuid.uuid4().hex[:6]
    u = User(
        community_id=CID, email=f"rc_{name}_{sfx}@nexara.dev", username=f"rc_{name}_{sfx}",
        display_name=name,
    )  # fmt: skip
    s.add(u)
    await s.flush()
    return u


def _svc(s: AsyncSession) -> RecipeService:
    return RecipeService(
        RecipeRepository(s),
        CommunityRepository(s),
        MentionTagsService(TagRepository(s)),
        None,
        CID,
    )


async def _ids(s: AsyncSession, viewer: User, **kw) -> set[uuid.UUID]:
    page = await _svc(s).list(viewer.id, **kw)
    return {r.id for r in page.recipes}


async def test_search_finds_by_ingredient_and_tag_counts(session: AsyncSession) -> None:
    a, b = await _user(session, "a"), await _user(session, "b")
    svc = _svc(session)
    r = await svc.create(
        a.id,
        RecipeCreate(
            title="Sunday supper",
            ingredients=[{"qty": "2 cups", "item": "cornbread mix"}],
            tags=["dinner"],
        ),
    )
    assert r.id in await _ids(session, b, q="cornbread")
    assert r.id not in await _ids(session, b, q="lasagna")
    assert r.id in await _ids(session, b, tag="dinner")
    assert any(t.tag == "dinner" and t.count >= 1 for t in await svc.tags(b.id))


async def test_private_recipe_hidden_from_others(session: AsyncSession) -> None:
    a, b = await _user(session, "a"), await _user(session, "b")
    r = await _svc(session).create(a.id, RecipeCreate(title="Secret", visibility="private"))
    assert r.id in await _ids(session, a)
    assert r.id not in await _ids(session, b)


async def test_subgroup_recipe_hidden_after_leaving(session: AsyncSession) -> None:
    a, b = await _user(session, "a"), await _user(session, "b")
    g = Subgroup(community_id=CID, name="G", slug=f"g-{uuid.uuid4().hex[:8]}", created_by=a.id)
    session.add(g)
    await session.flush()
    for u in (a, b):
        session.add(SubgroupMember(community_id=CID, subgroup_id=g.id, user_id=u.id))
    await session.flush()
    r = await _svc(session).create(
        a.id, RecipeCreate(title="Group only", visibility="subgroup", subgroup_id=g.id)
    )
    assert r.id in await _ids(session, b)
    member = await session.get(SubgroupMember, (g.id, b.id))
    await session.delete(member)
    await session.flush()
    assert r.id not in await _ids(session, b)


async def test_deleted_recipe_unlinks_list_item(session: AsyncSession) -> None:
    a = await _user(session, "a")
    r = await _svc(session).create(a.id, RecipeCreate(title="Pie"))
    lst = List(community_id=CID, owner_id=a.id, title="L", visibility="community")
    session.add(lst)
    await session.flush()
    item = ListItem(list_id=lst.id, position=0, recipe_id=r.id)
    session.add(item)
    await session.flush()
    await _svc(session).delete(r.id, a.id, is_admin=False)
    await session.refresh(item)
    assert item.recipe_id is None
    assert await _ids(session, a) == set()


async def test_story_mention_tags_user(session: AsyncSession) -> None:
    a, b = await _user(session, "a"), await _user(session, "b")
    r = await _svc(session).create(
        a.id, RecipeCreate(title="Gran's", story=f"Made it with @{b.username}")
    )
    tags = (
        (
            await session.execute(
                select(Tag).where(Tag.target_type == "recipe", Tag.target_id == r.id)
            )
        )
        .scalars()
        .all()
    )
    assert [t.subject_id for t in tags] == [b.id]


async def test_private_household_name_hidden(session: AsyncSession) -> None:
    from app.models.household import HouseholdMember

    ruth, maya = await _user(session, "ruth"), await _user(session, "maya")
    pet = HouseholdMember(
        community_id=CID, owner_id=ruth.id, kind="pet", name="Secret Cat", visibility="private"
    )
    session.add(pet)
    await session.flush()
    repo = RecipeRepository(session)
    assert await repo.household_names([pet.id], ruth.id, CID) == {pet.id: "Secret Cat"}
    assert await repo.household_names([pet.id], maya.id, CID) == {}
