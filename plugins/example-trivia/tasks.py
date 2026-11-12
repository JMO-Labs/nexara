"""
@file tasks.py
@brief Celery tasks: daily question selection and weekly streak reset.

Scheduled in ``app/tasks/celery_app.py`` (00:00 UTC daily; Sunday 00:05 UTC weekly).
"""

from __future__ import annotations

import asyncio
import importlib.util
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.db.session import async_session_factory
from app.plugins.context import PluginContext
from app.plugins.manifest import load_manifest
from app.tasks.celery_app import celery_app

PLUGIN_ID = "example-trivia"
_DIR = Path(__file__).resolve().parent


def _models() -> Any:
    key = "nexara_plugin_example_trivia_models"
    if key not in sys.modules:
        spec = importlib.util.spec_from_file_location(key, _DIR / "models.py")
        assert spec is not None and spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        sys.modules[key] = mod
        spec.loader.exec_module(mod)
    return sys.modules[key]


async def _with_ctx(fn: Any) -> Any:
    community_id = uuid.UUID(get_settings().COMMUNITY_ID)
    async with async_session_factory() as session:
        ctx = PluginContext(PLUGIN_ID, load_manifest(_DIR), session, community_id, None, None)
        result = await fn(ctx)
        await session.commit()
    return result


async def _select() -> dict[str, Any]:
    m = _models()
    today = datetime.now(UTC).date()
    q = await _with_ctx(lambda ctx: m.select_daily_question(ctx, today))
    return {"id": q["id"], "date": q["date"]}


async def _reset() -> dict[str, int]:
    m = _models()
    return {"reset": await _with_ctx(m.reset_all_streaks)}


@celery_app.task(  # type: ignore[untyped-decorator]
    name="plugins.example_trivia.select_daily_question", queue="maintenance"
)
def select_daily_question() -> dict[str, Any]:
    """@brief Pick a random question and store it as ``question:today``."""
    return asyncio.run(_select())


@celery_app.task(  # type: ignore[untyped-decorator]
    name="plugins.example_trivia.reset_streaks", queue="maintenance"
)
def reset_streaks() -> dict[str, int]:
    """@brief Weekly: reset every user's streak."""
    return asyncio.run(_reset())
