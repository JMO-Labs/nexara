"""
@file prompts.py
@brief Prompts API — CRUD (admin), active list (any user).
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import get_current_user, get_db, require_role
from app.core.i18n import _
from app.models.user import User
from app.repositories.notification_repo import NotificationRepository
from app.repositories.post_repo import PostRepository
from app.repositories.prompt_repo import PromptRepository
from app.repositories.settings_repo import SettingsRepository
from app.schemas.common import MessageResponse
from app.schemas.prompt import (
    PromptCreate,
    PromptPostResponse,
    PromptResponse,
    PromptUpdate,
)
from app.services.notification_service import NotificationService
from app.services.prompt_service import PromptService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/prompts", tags=["prompts"])


def _community_id(settings: Settings = Depends(get_settings)) -> uuid.UUID:
    """@brief Extract the community UUID from settings."""
    return uuid.UUID(settings.COMMUNITY_ID)


def _build_service(
    db: AsyncSession = Depends(get_db),
    community_id: uuid.UUID = Depends(_community_id),
) -> PromptService:
    """@brief Build PromptService with notification + DB deps."""
    notif = NotificationService(
        notification_repo=NotificationRepository(db),
        settings_repo=SettingsRepository(db),
        community_id=community_id,
    )
    return PromptService(
        prompt_repo=PromptRepository(db),
        post_repo=PostRepository(db),
        community_id=community_id,
        session=db,
        notification_service=notif,
    )


# ── Admin CRUD ────────────────────────────────────────────────────


@router.get("", response_model=list[PromptResponse])
async def list_prompts(
    user: User = Depends(require_role("admin")),
    service: PromptService = Depends(_build_service),
) -> list[PromptResponse]:
    """@brief List all prompts (admin)."""
    return await service.list_prompts()


@router.post("", response_model=PromptResponse, status_code=201)
async def create_prompt(
    body: PromptCreate,
    user: User = Depends(require_role("admin")),
    service: PromptService = Depends(_build_service),
) -> PromptResponse:
    """@brief Create a custom prompt (admin)."""
    return await service.create_prompt(user.id, body)


@router.get("/active", response_model=list[PromptPostResponse])
async def list_active(
    user: User = Depends(get_current_user),
    service: PromptService = Depends(_build_service),
) -> list[PromptPostResponse]:
    """@brief List currently-pinned prompt posts."""
    return await service.list_active()


@router.get("/posts/{prompt_post_id}/responses")
async def list_responses(
    prompt_post_id: uuid.UUID,
    limit: int = Query(20, ge=1, le=50),
    cursor: str | None = Query(None),
    user: User = Depends(get_current_user),
    service: PromptService = Depends(_build_service),
) -> dict[str, Any]:
    """@brief List posts replying to a prompt post (newest first)."""
    return await service.list_responses(prompt_post_id, user.id, limit=limit, cursor=cursor)


@router.get("/{prompt_id}", response_model=PromptResponse)
async def get_prompt(
    prompt_id: uuid.UUID,
    user: User = Depends(require_role("admin")),
    service: PromptService = Depends(_build_service),
) -> PromptResponse:
    """@brief Get a prompt (admin)."""
    return await service.get_prompt(prompt_id)


@router.patch("/{prompt_id}", response_model=PromptResponse)
async def update_prompt(
    prompt_id: uuid.UUID,
    body: PromptUpdate,
    user: User = Depends(require_role("admin")),
    service: PromptService = Depends(_build_service),
) -> PromptResponse:
    """@brief Update a prompt (admin)."""
    return await service.update_prompt(prompt_id, body)


@router.delete("/{prompt_id}", response_model=MessageResponse)
async def delete_prompt(
    prompt_id: uuid.UUID,
    user: User = Depends(require_role("admin")),
    service: PromptService = Depends(_build_service),
) -> MessageResponse:
    """@brief Delete a custom prompt (admin)."""
    await service.delete_prompt(prompt_id, user.id)
    return MessageResponse(message=_("Prompt deleted"))
