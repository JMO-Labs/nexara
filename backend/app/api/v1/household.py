"""
@file household.py
@brief Household members and pets: list, view, add, edit, remove, upcoming.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.repositories.household_repo import HouseholdRepository
from app.schemas.common import MessageResponse
from app.schemas.household import (
    Celebration,
    HouseholdCreate,
    HouseholdResponse,
    HouseholdUpdate,
)
from app.services.household_service import HouseholdService
from app.services.memories_service import local_today

router = APIRouter(tags=["household"])


def _service(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> HouseholdService:
    """@brief HouseholdService bound to the request session."""
    return HouseholdService(HouseholdRepository(db), user.community_id)


@router.get("/household", response_model=list[HouseholdResponse])
async def list_visible(
    user: User = Depends(get_current_user), svc: HouseholdService = Depends(_service)
) -> Any:
    """@brief Every household member the viewer may see."""
    return await svc.list_visible(user)


@router.get("/household/upcoming", response_model=list[Celebration])
async def upcoming(
    user: User = Depends(get_current_user), svc: HouseholdService = Depends(_service)
) -> Any:
    """@brief Birthdays and gotcha days in the next 14 days."""
    return await svc.upcoming(user, local_today(user.timezone))


@router.get("/users/{user_id}/household", response_model=list[HouseholdResponse])
async def list_for_owner(
    user_id: uuid.UUID,
    user: User = Depends(get_current_user),
    svc: HouseholdService = Depends(_service),
) -> Any:
    """@brief A member's household as the viewer may see it."""
    return await svc.list_for_owner(user_id, user)


@router.post("/household", response_model=HouseholdResponse, status_code=201)
async def create(
    body: HouseholdCreate,
    user: User = Depends(get_current_user),
    svc: HouseholdService = Depends(_service),
) -> Any:
    """@brief Add a family member or pet."""
    return await svc.create(user, body)


@router.get("/household/{member_id}", response_model=HouseholdResponse)
async def get_one(
    member_id: uuid.UUID,
    user: User = Depends(get_current_user),
    svc: HouseholdService = Depends(_service),
) -> Any:
    """@brief One household member."""
    return await svc.get(member_id, user)


@router.patch("/household/{member_id}", response_model=HouseholdResponse)
async def update(
    member_id: uuid.UUID,
    body: HouseholdUpdate,
    user: User = Depends(get_current_user),
    svc: HouseholdService = Depends(_service),
) -> Any:
    """@brief Edit a household member you manage."""
    return await svc.update(member_id, user, body)


@router.delete("/household/{member_id}", response_model=MessageResponse)
async def remove(
    member_id: uuid.UUID,
    user: User = Depends(get_current_user),
    svc: HouseholdService = Depends(_service),
) -> MessageResponse:
    """@brief Remove a household member you manage."""
    await svc.delete(member_id, user)
    return MessageResponse(message="Removed")
