"""
@file celebrations.py
@brief Calendar celebrations (birthdays, gotcha days) in a date range.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.repositories.celebration_repo import CelebrationRepository
from app.repositories.household_repo import HouseholdRepository
from app.schemas.celebration import CalendarCelebration
from app.services.celebration_service import CelebrationService

router = APIRouter(prefix="/calendar", tags=["calendar"])


def _service(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> CelebrationService:
    return CelebrationService(CelebrationRepository(db), HouseholdRepository(db), user.community_id)


@router.get("/celebrations", response_model=list[CalendarCelebration])
async def celebrations(
    start: date = Query(...),
    end: date = Query(...),
    user: User = Depends(get_current_user),
    svc: CelebrationService = Depends(_service),
) -> list[CalendarCelebration]:
    """@brief Birthdays and gotcha days the caller may see, start..end inclusive."""
    return await svc.in_range(user, start, end)
