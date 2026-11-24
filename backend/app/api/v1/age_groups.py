"""
@file age_groups.py
@brief Age group routes: member suggestions and admin control.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status

from app.core.dependencies import get_current_user, require_role
from app.core.deps_age import get_age_service
from app.models.user import User
from app.schemas.age_group import (
    AgeGroupSet,
    AgeGroupSettings,
    AgeSuggestionCreate,
    AgeSuggestionResponse,
)
from app.schemas.common import MessageResponse
from app.services.age_service import AgeService

router = APIRouter(prefix="/age-groups", tags=["age-groups"])
admin_router = APIRouter(
    prefix="/admin", tags=["admin-age-groups"], dependencies=[Depends(require_role("admin"))]
)


@router.post(
    "/suggestions", response_model=AgeSuggestionResponse, status_code=status.HTTP_201_CREATED
)
async def suggest(
    body: AgeSuggestionCreate,
    _user: User = Depends(get_current_user),
    svc: AgeService = Depends(get_age_service),
) -> AgeSuggestionResponse:
    """@brief Suggest an age group for another member (admins are notified)."""
    row = await svc.suggest(body.subject_id, body.age_group, body.note)
    return AgeSuggestionResponse.model_validate(row)


@admin_router.get("/age-groups/suggestions", response_model=list[AgeSuggestionResponse])
async def list_suggestions(
    status: str | None = "pending", svc: AgeService = Depends(get_age_service)
) -> list[AgeSuggestionResponse]:
    """@brief Admin: list suggestions (default pending)."""
    return [AgeSuggestionResponse.model_validate(r) for r in await svc.list_suggestions(status)]


@admin_router.post("/age-groups/suggestions/{suggestion_id}/approve")
async def approve(
    suggestion_id: uuid.UUID, svc: AgeService = Depends(get_age_service)
) -> AgeSuggestionResponse:
    """@brief Admin: approve a suggestion (sets the user's age group)."""
    return AgeSuggestionResponse.model_validate(await svc.decide(suggestion_id, True))


@admin_router.post("/age-groups/suggestions/{suggestion_id}/reject")
async def reject(
    suggestion_id: uuid.UUID, svc: AgeService = Depends(get_age_service)
) -> AgeSuggestionResponse:
    """@brief Admin: reject a suggestion."""
    return AgeSuggestionResponse.model_validate(await svc.decide(suggestion_id, False))


@admin_router.get("/age-groups/settings", response_model=AgeGroupSettings)
async def get_settings_route(svc: AgeService = Depends(get_age_service)) -> AgeGroupSettings:
    """@brief Admin: current age settings."""
    return AgeGroupSettings(adult_requires_approval=await svc.settings())


@admin_router.put("/age-groups/settings", response_model=AgeGroupSettings)
async def put_settings(
    body: AgeGroupSettings, svc: AgeService = Depends(get_age_service)
) -> AgeGroupSettings:
    """@brief Admin: toggle adult approval mode."""
    return AgeGroupSettings(
        adult_requires_approval=await svc.set_adult_requires_approval(body.adult_requires_approval)
    )


@admin_router.put("/users/{user_id}/age-group", response_model=MessageResponse)
async def set_user_age_group(
    user_id: uuid.UUID, body: AgeGroupSet, svc: AgeService = Depends(get_age_service)
) -> MessageResponse:
    """@brief Admin: set or clear a user's age group."""
    await svc.set_user_group(user_id, body.age_group)
    return MessageResponse(message="ok")
