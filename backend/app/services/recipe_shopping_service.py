"""
@file recipe_shopping_service.py
@brief Turn a recipe's ingredients into shopping-list items.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.core.exceptions import AppError, ValidationError
from app.schemas.recipe_shopping import ToListIn, ToListOut
from app.services.list_items_service import ListItemService
from app.services.list_service import ListService
from app.services.recipe_service import RecipeService

_TITLE_MAX = 120
_NEW_SCHEMA: list[dict[str, Any]] = [
    {"key": "item", "label": "Item", "position": 0, "required": True, "type_key": "text"}
]


def _target_field(schema: list[dict[str, Any]]) -> str:
    """@return Key of the first required text field, else first text field.
    @raises AppError LIST_HAS_NO_TEXT_FIELD (422) when there is none."""
    texts = [f for f in schema if f.get("type_key") == "text"]
    if not texts:
        raise AppError("LIST_HAS_NO_TEXT_FIELD", "List has no text field", 422)
    return str(next((f for f in texts if f.get("required")), texts[0])["key"])


class RecipeShoppingService:
    """@brief Adds recipe ingredients to a (new or existing) list via the list services."""

    def __init__(self, recipes: RecipeService, lists: ListService, items: ListItemService) -> None:
        self._recipes = recipes
        self._lists = lists
        self._items = items

    async def add(
        self, recipe_id: uuid.UUID, user_id: uuid.UUID, community_id: uuid.UUID, body: ToListIn
    ) -> ToListOut:
        """
        @brief Add selected ingredients as list items linked to the recipe.

        @raises NotFoundError Recipe missing/not visible.
        @raises ValidationError Index out of range.
        """
        recipe = await self._recipes.get(recipe_id, user_id)
        all_ing = recipe.ingredients
        idx = list(range(len(all_ing))) if body.ingredients is None else body.ingredients
        if any(i < 0 or i >= len(all_ing) for i in idx):
            raise ValidationError("Ingredient index out of range")
        lines = [f"{all_ing[i].qty} {all_ing[i].item}".strip() for i in idx]
        lines = [x for x in lines if x]
        if body.list_id is None:
            lst = await self._lists.create(
                user_id,
                title=f"Shopping: {recipe.title}"[:_TITLE_MAX],
                visibility="private",
                field_schema=list(_NEW_SCHEMA),
            )
        else:
            lst = await self._lists.get_by_id(body.list_id, user_id)
        key = _target_field(lst.field_schema)
        pos = lst.item_count
        for n, line in enumerate(lines):
            await self._items.create(
                community_id, lst.id, user_id, {key: line}, pos + n, recipe_id=recipe.id
            )
        return ToListOut(list_id=lst.id, added=len(lines))
