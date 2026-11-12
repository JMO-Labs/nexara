"""
@file router.py
@brief Trivia endpoints, mounted at ``/api/v1/plugins/example-trivia``.

All data access goes through ``PluginContext.db``. The answering user is always the
authenticated user (a client-supplied user id is never trusted).
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.user import User
from app.plugins.context import PluginContext
from app.plugins.manifest import load_manifest

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


router = APIRouter()


class AnswerIn(BaseModel):
    """@brief Answer submission body."""

    question_id: str
    answer_text: str


async def get_ctx(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> PluginContext:
    """@brief Community-scoped PluginContext for the requesting user."""
    return PluginContext(PLUGIN_ID, load_manifest(_DIR), db, user.community_id, None, None)


def _today() -> Any:
    return datetime.now(UTC).date()


@router.get("/questions/today")
async def questions_today(
    ctx: PluginContext = Depends(get_ctx), _: User = Depends(get_current_user)
) -> dict[str, Any]:
    """@brief Today's question (without the answer key)."""
    q = await _models().get_today_public(ctx)
    if q is None:
        raise NotFoundError("No question selected yet")
    return q  # type: ignore[no-any-return]


@router.post("/answers")
async def post_answer(
    body: AnswerIn,
    ctx: PluginContext = Depends(get_ctx),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """@brief Submit and score an answer for the authenticated user."""
    m = _models()
    try:
        return await m.submit_answer(  # type: ignore[no-any-return]
            ctx, str(user.id), body.question_id, body.answer_text, _today()
        )
    except m.AlreadyAnsweredError as exc:
        raise ConflictError(str(exc)) from exc
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc


@router.get("/leaderboard")
async def get_leaderboard(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    ctx: PluginContext = Depends(get_ctx),
    _: User = Depends(get_current_user),
) -> dict[str, Any]:
    """@brief Paginated top-100 leaderboard."""
    return await _models().leaderboard(ctx, _today(), page, size)  # type: ignore[no-any-return]


@router.get("/my-stats")
async def get_my_stats(
    ctx: PluginContext = Depends(get_ctx), user: User = Depends(get_current_user)
) -> dict[str, Any]:
    """@brief Streak, total correct and rank of the current user."""
    return await _models().my_stats(ctx, str(user.id), _today())  # type: ignore[no-any-return]
