"""
@file recipes.py
@brief Recipe book endpoints under /recipes.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import get_current_user, get_db, get_dispatcher
from app.core.list_dependencies import get_list_item_service, get_list_service
from app.models.user import User
from app.repositories.community_repo import CommunityRepository
from app.repositories.notification_repo import NotificationRepository
from app.repositories.recipe_repo import RecipeRepository
from app.repositories.settings_repo import SettingsRepository
from app.repositories.tag_repo import TagRepository
from app.schemas.recipe import RecipeCreate, RecipeOut, RecipePage, RecipeUpdate, TagCount
from app.schemas.recipe_shopping import ToListIn, ToListOut
from app.services.list_items_service import ListItemService
from app.services.list_service import ListService
from app.services.mention_tags import MentionTagsService
from app.services.notification_service import NotificationService
from app.services.recipe_service import RecipeService
from app.services.recipe_shopping_service import RecipeShoppingService

router = APIRouter(prefix="/recipes", tags=["recipes"])


def _build_service(
    db: AsyncSession = Depends(get_db), settings: Settings = Depends(get_settings)
) -> RecipeService:
    """@brief Build RecipeService with injected dependencies."""
    cid = uuid.UUID(settings.COMMUNITY_ID)
    notif = NotificationService(
        NotificationRepository(db), SettingsRepository(db), cid, dispatcher=get_dispatcher()
    )
    return RecipeService(
        RecipeRepository(db),
        CommunityRepository(db),
        MentionTagsService(TagRepository(db)),
        notif,
        cid,
    )


def _build_shopping(
    recipes: RecipeService = Depends(_build_service),
    lists: ListService = Depends(get_list_service),
    items: ListItemService = Depends(get_list_item_service),
) -> RecipeShoppingService:
    """@brief Build RecipeShoppingService from the recipe and list services."""
    return RecipeShoppingService(recipes, lists, items)


@router.post("", status_code=201, response_model=RecipeOut)
async def create_recipe(
    body: RecipeCreate,
    user: User = Depends(get_current_user),
    service: RecipeService = Depends(_build_service),
) -> Any:
    """@brief Add a recipe."""
    return await service.create(user.id, body)


@router.get("", response_model=RecipePage)
async def list_recipes(
    q: str | None = None,
    tag: str | None = None,
    cursor: str | None = None,
    user: User = Depends(get_current_user),
    service: RecipeService = Depends(_build_service),
) -> Any:
    """@brief Visible recipes, optionally searched or filtered by tag."""
    return await service.list(user.id, q, tag, cursor)


@router.get("/tags", response_model=list[TagCount])
async def recipe_tags(
    user: User = Depends(get_current_user),
    service: RecipeService = Depends(_build_service),
) -> Any:
    """@brief Distinct tags with counts."""
    return await service.tags(user.id)


@router.get("/{recipe_id}", response_model=RecipeOut)
async def get_recipe(
    recipe_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: RecipeService = Depends(_build_service),
) -> Any:
    """@brief One recipe."""
    return await service.get(recipe_id, user.id)


@router.post("/{recipe_id}/shopping-list", status_code=201, response_model=ToListOut)
async def recipe_to_shopping_list(
    recipe_id: uuid.UUID,
    body: ToListIn,
    user: User = Depends(get_current_user),
    service: RecipeShoppingService = Depends(_build_shopping),
    settings: Settings = Depends(get_settings),
) -> Any:
    """@brief Add recipe ingredients to a new or existing shopping list."""
    return await service.add(recipe_id, user.id, uuid.UUID(settings.COMMUNITY_ID), body)


@router.put("/{recipe_id}", response_model=RecipeOut)
async def update_recipe(
    recipe_id: uuid.UUID,
    body: RecipeUpdate,
    user: User = Depends(get_current_user),
    service: RecipeService = Depends(_build_service),
) -> Any:
    """@brief Replace a recipe (author or admin)."""
    return await service.update(recipe_id, user.id, body, is_admin=user.role == "admin")


@router.delete("/{recipe_id}", status_code=204)
async def delete_recipe(
    recipe_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: RecipeService = Depends(_build_service),
) -> Response:
    """@brief Delete a recipe (author or admin)."""
    await service.delete(recipe_id, user.id, is_admin=user.role == "admin")
    return Response(status_code=204)
