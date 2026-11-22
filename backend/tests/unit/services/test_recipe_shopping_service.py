"""
@file test_recipe_shopping_service.py
@brief Unit tests for RecipeShoppingService.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import AppError, ValidationError
from app.models.list import List
from app.schemas.recipe import Ingredient
from app.schemas.recipe_shopping import ToListIn
from app.services.list_items_service import ListItemService
from app.services.list_service import ListService
from app.services.recipe_service import RecipeService
from app.services.recipe_shopping_service import RecipeShoppingService

CID, UID, RID = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()


def _lst(schema, count=2):
    lst = MagicMock(spec=List)
    lst.id, lst.field_schema, lst.item_count = uuid.uuid4(), schema, count
    return lst


@pytest.fixture
def env():
    recipes = AsyncMock(spec=RecipeService)
    recipe = MagicMock(id=RID, title="Cornbread")
    recipe.ingredients = [
        Ingredient(qty="1 cup", item="cornmeal"),
        Ingredient(qty="", item="salt"),
    ]
    recipes.get.return_value = recipe
    lists, items = AsyncMock(spec=ListService), AsyncMock(spec=ListItemService)
    return RecipeShoppingService(recipes, lists, items), lists, items


async def test_new_list_all_ingredients(env):
    svc, lists, items = env
    lst = _lst([{"key": "item", "type_key": "text", "required": True}], 0)
    lists.create.return_value = lst
    out = await svc.add(RID, UID, CID, ToListIn())
    assert out.added == 2 and out.list_id == lst.id
    kw = lists.create.await_args.kwargs
    assert kw["title"] == "Shopping: Cornbread" and kw["visibility"] == "private"
    assert items.create.await_args_list[0].args[3] == {"item": "1 cup cornmeal"}
    assert items.create.await_args_list[1].args[3:5] == ({"item": "salt"}, 1)
    assert items.create.await_args.kwargs["recipe_id"] == RID


async def test_existing_list_picks_required_text_field(env):
    svc, lists, items = env
    schema = [
        {"key": "who", "type_key": "text"},
        {"key": "item", "type_key": "text", "required": True},
    ]
    lists.get_by_id.return_value = _lst(schema)
    await svc.add(RID, UID, CID, ToListIn(list_id=uuid.uuid4(), ingredients=[1]))
    lists.create.assert_not_awaited()
    assert items.create.await_count == 1
    assert items.create.await_args.args[3:5] == ({"item": "salt"}, 2)


async def test_no_text_field(env):
    svc, lists, _items = env
    lists.get_by_id.return_value = _lst([{"key": "n", "type_key": "number"}])
    with pytest.raises(AppError) as e:
        await svc.add(RID, UID, CID, ToListIn(list_id=uuid.uuid4()))
    assert e.value.code == "LIST_HAS_NO_TEXT_FIELD"


async def test_index_out_of_range(env):
    svc, _lists, _items = env
    with pytest.raises(ValidationError):
        await svc.add(RID, UID, CID, ToListIn(ingredients=[5]))
