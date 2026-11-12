"""
@file hooks.py
@brief ``on_user_joined`` hook: welcome notification with today's question.
"""

from __future__ import annotations

import importlib.util
import sys
import uuid
from pathlib import Path
from typing import Any


def _models() -> Any:
    key = "nexara_plugin_example_trivia_models"
    if key not in sys.modules:
        spec = importlib.util.spec_from_file_location(key, Path(__file__).with_name("models.py"))
        assert spec is not None and spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        sys.modules[key] = mod
        spec.loader.exec_module(mod)
    return sys.modules[key]


async def on_user_joined(ctx: Any, user_id: uuid.UUID, **_: Any) -> None:
    """@brief Notify the new member with today's question (no-op when none is set)."""
    q = await _models().get_today_public(ctx)
    if q is None:
        return
    await ctx.notify(
        user_id,
        "system",
        {
            "message": f"Welcome! Today's trivia: {q['text']}",
            "options": q["options"],
            "link": "/app/plugins/example-trivia",
        },
    )
