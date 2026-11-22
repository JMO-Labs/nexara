"""
@file test_recipe_shopping.py
@brief Real-Postgres: recipe ingredients become linked shopping-list items.
"""

from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
import app.services.list_field_types  # noqa: F401
from app.models.list import ListItem
from app.models.user import User
from app.repositories.community_repo import CommunityRepository
from app.repositories.list_item_repo import ListItemRepository
from app.repositories.list_member_repo import ListMemberRepository
from app.repositories.list_repo import ListRepository
from app.repositories.recipe_repo import RecipeRepository
from app.repositories.tag_repo import TagRepository
from app.schemas.recipe import Ingredient, RecipeCreate
from app.schemas.recipe_shopping import ToListIn
from app.services.list_field_registry import ListFieldRegistry
from app.services.list_items_service import ListItemService
from app.services.list_service import ListService
from app.services.mention_tags import MentionTagsService
from app.services.recipe_service import RecipeService
from app.services.recipe_shopping_service import RecipeShoppingService

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


async def test_add_creates_linked_items(session: AsyncSession):
    sfx = uuid.uuid4().hex[:6]
    user = User(
        community_id=CID, email=f"rs_{sfx}@nexara.dev", username=f"rs_{sfx}", display_name="Rs"
    )
    session.add(user)
    await session.flush()
    recipes = RecipeService(
        RecipeRepository(session),
        CommunityRepository(session),
        MentionTagsService(TagRepository(session)),
        None,
        CID,
    )
    recipe = await recipes.create(
        user.id,
        RecipeCreate(
            title="Soup",
            ingredients=[Ingredient(qty="2", item="leeks"), Ingredient(item="stock")],
        ),
    )
    lists = ListService(
        ListRepository(session),
        ListMemberRepository(session),
        ListFieldRegistry(),
        CID,
        session,
    )
    items = ListItemService(
        ListItemRepository(session), ListRepository(session), ListFieldRegistry()
    )
    out = await RecipeShoppingService(recipes, lists, items).add(
        recipe.id, user.id, CID, ToListIn()
    )
    assert out.added == 2
    rows = (
        await session.scalars(
            select(ListItem).where(ListItem.list_id == out.list_id).order_by(ListItem.position)
        )
    ).all()
    assert [r.values["item"] for r in rows] == ["2 leeks", "stock"]
    assert all(r.recipe_id == recipe.id for r in rows)
