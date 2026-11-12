"""
@file router.py
@brief Recipe box endpoints (mounted at /api/v1/plugins/example-recipe-box).
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.core.exceptions import AuthorizationError, NotFoundError, RateLimitError
from app.models.plugin import Plugin
from app.models.user import User
from app.plugins.context import PluginContext
from app.plugins.manifest import PluginManifest, PluginPermission, load_manifest

from . import store
from .hooks import register_hooks  # noqa: F401  (loader calls it on this module)
from .models import RecipeIn

PLUGIN_ID = "example-recipe-box"
HARD_LIMIT = 100

router = APIRouter(tags=["example-recipe-box"])


@lru_cache(maxsize=1)
def _manifest() -> PluginManifest:
    return load_manifest(Path(__file__).parent)


async def get_ctx(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> PluginContext:
    """@brief Build a community-scoped PluginContext with saved settings."""
    saved = (
        await db.execute(
            select(Plugin.settings).where(
                Plugin.id == PLUGIN_ID, Plugin.community_id == user.community_id
            )
        )
    ).scalar_one_or_none()
    return PluginContext(PLUGIN_ID, _manifest(), db, user.community_id, None, None, saved)


async def recipe_ctx(ctx: PluginContext = Depends(get_ctx)) -> PluginContext:
    """@brief Require db_read and db_write on every endpoint. @throws AuthorizationError"""
    missing = [
        p.value
        for p in (PluginPermission.DB_READ, PluginPermission.DB_WRITE)
        if p not in ctx.manifest.permissions
    ]
    if missing:
        raise AuthorizationError(message=f"Plugin lacks permission: {', '.join(missing)}")
    return ctx


@contextmanager
def _denied() -> Iterator[None]:
    try:
        yield
    except PermissionError as exc:
        raise AuthorizationError(message=str(exc)) from exc


def _limit(ctx: PluginContext) -> int:
    default = _manifest().settings["max_recipes_per_user"].default
    raw: Any = ctx.settings.get("max_recipes_per_user", default)
    return max(0, min(int(raw), HARD_LIMIT))


def _page(items: list[dict[str, Any]], limit: int, offset: int) -> dict[str, Any]:
    return {"items": items[offset : offset + limit], "total": len(items)}


async def _visible(ctx: PluginContext, user: User, rid: str) -> dict[str, Any]:
    rec = await store.get(ctx, rid)
    if rec is None or (user.role != "admin" and rec["owner_id"] != str(user.id)):
        raise NotFoundError(message="Recipe not found")
    return rec


def _owner_only(rec: dict[str, Any], user: User) -> None:
    if rec["owner_id"] != str(user.id):
        raise AuthorizationError(message="Only the owner can modify this recipe")


@router.post("/recipes", status_code=201)
async def create_recipe(
    body: RecipeIn, user: User = Depends(get_current_user), ctx: PluginContext = Depends(recipe_ctx)
) -> dict[str, Any]:
    """@brief Create a recipe; 429 when the per-user limit is reached."""
    with _denied():
        try:
            return await store.create(ctx, user.id, body, _limit(ctx))
        except OverflowError:
            raise RateLimitError(message="Recipe limit reached") from None


@router.get("/recipes")
async def list_recipes(
    tag: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    ctx: PluginContext = Depends(recipe_ctx),
) -> dict[str, Any]:
    """@brief Paginated list, optionally filtered by tag."""
    with _denied():
        items = await store.list_visible(ctx, user.id, user.role == "admin", tag)
        return _page(items, limit, offset)


@router.get("/recipes/search")
async def search_recipes(
    q: str = Query(min_length=1),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    ctx: PluginContext = Depends(recipe_ctx),
) -> dict[str, Any]:
    """@brief Search by recipe or ingredient name."""
    with _denied():
        return _page(await store.search(ctx, user.id, user.role == "admin", q), limit, offset)


@router.get("/recipes/{recipe_id}")
async def get_recipe(
    recipe_id: str, user: User = Depends(get_current_user), ctx: PluginContext = Depends(recipe_ctx)
) -> dict[str, Any]:
    """@brief Fetch one recipe (owner or admin)."""
    with _denied():
        return await _visible(ctx, user, recipe_id)


@router.put("/recipes/{recipe_id}")
async def update_recipe(
    recipe_id: str,
    body: RecipeIn,
    user: User = Depends(get_current_user),
    ctx: PluginContext = Depends(recipe_ctx),
) -> dict[str, Any]:
    """@brief Update a recipe (owner only)."""
    with _denied():
        rec = await _visible(ctx, user, recipe_id)
        _owner_only(rec, user)
        return await store.update(ctx, rec, body)


@router.delete("/recipes/{recipe_id}", status_code=204)
async def delete_recipe(
    recipe_id: str, user: User = Depends(get_current_user), ctx: PluginContext = Depends(recipe_ctx)
) -> Response:
    """@brief Delete a recipe (owner only)."""
    with _denied():
        rec = await _visible(ctx, user, recipe_id)
        _owner_only(rec, user)
        await store.delete(ctx, recipe_id)
    return Response(status_code=204)
