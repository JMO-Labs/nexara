"""
@file suggestions.py
@brief Admin endpoints to list, generate, approve and reject AI suggestions.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.core.config import Settings, get_settings
from app.core.dependencies import get_suggestion_service, require_role
from app.core.exceptions import ValidationError
from app.models.suggestion import Suggestion
from app.models.user import User
from app.services.ai.suggestion_service import SuggestionService

router = APIRouter(prefix="/admin/suggestions", tags=["admin-suggestions"])


class SuggestionOut(BaseModel):
    """@brief Suggestion response shape."""

    id: uuid.UUID
    type: str
    content: dict[str, Any]
    suggested_by: str
    approved_at: datetime | None = None
    approved_by: uuid.UUID | None = None
    rejected_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class GenerateOut(BaseModel):
    """@brief Generation result: number of suggestions created (0 if skipped)."""

    created: int


def _cid(settings: Settings = Depends(get_settings)) -> uuid.UUID:
    return uuid.UUID(settings.COMMUNITY_ID)


@router.get("", response_model=list[SuggestionOut])
async def list_suggestions(
    type: Literal["prompt", "poll"] | None = None,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _user: User = Depends(require_role("admin")),
    svc: SuggestionService = Depends(get_suggestion_service),
    cid: uuid.UUID = Depends(_cid),
) -> list[Suggestion]:
    """@brief List pending suggestions (admin)."""
    return await svc.list_pending(cid, type, limit, offset)


@router.post("/generate", response_model=GenerateOut)
async def generate(
    type: Literal["prompt", "poll"] = "prompt",
    topic: str | None = Query(None, min_length=1, max_length=200),
    _user: User = Depends(require_role("admin")),
    svc: SuggestionService = Depends(get_suggestion_service),
    cid: uuid.UUID = Depends(_cid),
) -> GenerateOut:
    """@brief Manually trigger generation (admin); ``topic`` is required for polls."""
    if type == "prompt":
        return GenerateOut(created=len(await svc.generate_prompt_suggestions(cid)))
    if not topic:
        raise ValidationError("topic is required for poll suggestions")
    return GenerateOut(created=1 if await svc.generate_poll_suggestions(cid, topic) else 0)


@router.post("/{suggestion_id}/approve", response_model=SuggestionOut)
async def approve(
    suggestion_id: uuid.UUID,
    user: User = Depends(require_role("admin")),
    svc: SuggestionService = Depends(get_suggestion_service),
    cid: uuid.UUID = Depends(_cid),
) -> Suggestion:
    """@brief Approve a pending suggestion (admin)."""
    return await svc.approve(suggestion_id, user.id, cid)


@router.post("/{suggestion_id}/reject", response_model=SuggestionOut)
async def reject(
    suggestion_id: uuid.UUID,
    _user: User = Depends(require_role("admin")),
    svc: SuggestionService = Depends(get_suggestion_service),
    cid: uuid.UUID = Depends(_cid),
) -> Suggestion:
    """@brief Reject a pending suggestion (admin)."""
    return await svc.reject(suggestion_id, cid)
