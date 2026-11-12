"""
@file hooks.py
@brief after_post_created hook: suggest the ``recipe`` tag on posts that mention one.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.plugins.context import PluginContext
from app.plugins.hooks import HookRegistry
from app.plugins.manifest import PluginManifest

PLUGIN_ID = "example-recipe-box"


async def on_post_created(
    ctx: PluginContext,
    *,
    user_id: uuid.UUID,
    post_id: uuid.UUID,
    content: str,
    **_: Any,
) -> None:
    """@brief Store a tag suggestion (``suggestion:{post_id}``) when content mentions "recipe"."""
    if "recipe" in (content or "").lower():
        await ctx.db.set(
            f"suggestion:{post_id}",
            {"tag": "recipe", "post_id": str(post_id), "user_id": str(user_id)},
        )


def register_hooks(community_id: uuid.UUID, manifest: PluginManifest) -> None:
    """@brief Register this plugin's handlers for one community."""
    HookRegistry.register(
        community_id, "after_post_created", PLUGIN_ID, on_post_created, manifest
    )
