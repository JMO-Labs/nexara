"""
@file store.py
@brief Recipe persistence over PluginContext.db (key/value).

Keys: ``recipe:{id}`` holds a recipe; ``index`` maps recipe id -> owner id.
Read-modify-write on ``index`` is not atomic (acceptable for a reference plugin).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from app.plugins.context import PluginContext

from .models import RecipeIn

__all__ = ["RecipeIn", "create", "get", "update", "delete", "list_visible", "search", "count_owned"]

INDEX = "index"


async def _index(ctx: PluginContext) -> dict[str, str]:
    return dict(await ctx.db.get(INDEX) or {})


async def count_owned(ctx: PluginContext, owner_id: uuid.UUID) -> int:
    """@brief Number of recipes owned by a user."""
    return sum(1 for o in (await _index(ctx)).values() if o == str(owner_id))


async def create(
    ctx: PluginContext, owner_id: uuid.UUID, data: RecipeIn, limit: int
) -> dict[str, Any]:
    """@brief Store a new recipe. @throws OverflowError when the owner is at ``limit``."""
    if await count_owned(ctx, owner_id) >= limit:
        raise OverflowError(limit)
    rid = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()
    rec = {
        "id": rid,
        "owner_id": str(owner_id),
        **data.model_dump(),
        "created_at": now,
        "updated_at": now,
    }
    await ctx.db.set(f"recipe:{rid}", rec)
    idx = await _index(ctx)
    idx[rid] = str(owner_id)
    await ctx.db.set(INDEX, idx)
    return rec


async def get(ctx: PluginContext, rid: str) -> dict[str, Any] | None:
    """@brief Fetch a recipe by id (no visibility check)."""
    rec: dict[str, Any] | None = await ctx.db.get(f"recipe:{rid}")
    return rec


async def update(ctx: PluginContext, rec: dict[str, Any], data: RecipeIn) -> dict[str, Any]:
    """@brief Replace the editable fields of a recipe."""
    rec = {**rec, **data.model_dump(), "updated_at": datetime.now(UTC).isoformat()}
    await ctx.db.set(f"recipe:{rec['id']}", rec)
    return rec


async def delete(ctx: PluginContext, rid: str) -> None:
    """@brief Remove a recipe and its index entry."""
    await ctx.db.delete(f"recipe:{rid}")
    idx = await _index(ctx)
    if idx.pop(rid, None) is not None:
        await ctx.db.set(INDEX, idx)


async def list_visible(
    ctx: PluginContext, viewer_id: uuid.UUID, is_admin: bool, tag: str | None = None
) -> list[dict[str, Any]]:
    """@brief Recipes the viewer may see (all for admin), newest first, optional tag filter."""
    out = []
    for rid, owner in (await _index(ctx)).items():
        if not is_admin and owner != str(viewer_id):
            continue
        rec = await get(ctx, rid)
        if rec and (tag is None or tag.lower() in rec["tags"]):
            out.append(rec)
    return sorted(out, key=lambda r: r["created_at"], reverse=True)


async def search(
    ctx: PluginContext, viewer_id: uuid.UUID, is_admin: bool, q: str
) -> list[dict[str, Any]]:
    """@brief Case-insensitive substring match on recipe or ingredient names."""
    needle = q.lower()
    return [
        r
        for r in await list_visible(ctx, viewer_id, is_admin)
        if needle in r["name"].lower() or any(needle in i["name"].lower() for i in r["ingredients"])
    ]
