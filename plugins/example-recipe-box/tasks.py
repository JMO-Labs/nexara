"""
@file tasks.py
@brief Daily Celery task: pick a random recipe and cache it as "recipe of the day".
"""

from __future__ import annotations

import asyncio
import json
import random
import uuid
from pathlib import Path
from typing import Any

from celery.schedules import crontab
from sqlalchemy import select

from app.core.config import get_settings
from app.models.plugin import Plugin
from app.plugins.context import PluginContext
from app.plugins.manifest import load_manifest
from app.tasks.celery_app import celery_app

from . import store

PLUGIN_ID = "example-recipe-box"
CACHE_TTL = 26 * 3600

# Merged into the Beat schedule when this module is imported by the worker/beat.
celery_app.conf.beat_schedule[f"{PLUGIN_ID}-recipe-of-day"] = {
    "task": f"plugins.{PLUGIN_ID}.generate_recipe_of_day",
    "schedule": crontab(hour="6", minute="0"),
}


def cache_key(community_id: uuid.UUID) -> str:
    """@brief Cache key holding the recipe of the day."""
    return f"plugin:{PLUGIN_ID}:{community_id}:recipe_of_day"


async def pick_recipe_of_day(ctx: PluginContext, cache: Any) -> str | None:
    """@brief Pick a random recipe, cache it as JSON. @return Recipe id or None if none exist."""
    ids = list(await ctx.db.get(store.INDEX) or {})
    if not ids:
        return None
    rid = random.choice(ids)  # noqa: S311 - not security sensitive
    rec = await store.get(ctx, rid)
    if rec is None:
        return None
    await cache.set(cache_key(ctx.community_id), json.dumps(rec), ex=CACHE_TTL)
    return rid


async def _enabled(session: Any, community_id: uuid.UUID) -> bool:
    """@brief True when the plugin is enabled (and not deleted) for the community."""
    stmt = select(Plugin.is_enabled).where(
        Plugin.id == PLUGIN_ID,
        Plugin.community_id == community_id,
        Plugin.deleted_at.is_(None),
    )
    return bool((await session.execute(stmt)).scalar_one_or_none())


async def _run() -> str | None:
    from app.core.valkey import DB_CACHE, get_pool
    from app.db.session import async_session_factory

    settings = get_settings()
    community_id = uuid.UUID(settings.COMMUNITY_ID)
    manifest = load_manifest(Path(__file__).parent)
    async with async_session_factory() as session:
        if not await _enabled(session, community_id):
            return None
        ctx = PluginContext(PLUGIN_ID, manifest, session, community_id, None, None)
        return await pick_recipe_of_day(ctx, get_pool(settings, DB_CACHE))


@celery_app.task(  # type: ignore[untyped-decorator]
    name=f"plugins.{PLUGIN_ID}.generate_recipe_of_day", queue="maintenance"
)
def generate_recipe_of_day() -> str | None:
    """@brief Beat-driven entry: refresh the cached recipe of the day."""
    return asyncio.run(_run())
