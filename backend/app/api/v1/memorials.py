"""
@file memorials.py
@brief Memorial endpoints: household passed-on date and admin account
       memorialize / restore.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.relations import build_relation_service
from app.core.config import Settings, get_settings
from app.core.dependencies import get_current_user, get_db, require_role
from app.models.user import User
from app.repositories.audit_repo import AuditRepository
from app.repositories.community_repo import CommunityRepository
from app.repositories.household_repo import HouseholdRepository
from app.repositories.token_repo import TokenRepository
from app.repositories.user_repo import UserRepository
from app.schemas.household import HouseholdResponse
from app.schemas.memorial import PassedOnBody
from app.services.household_service import HouseholdService
from app.services.memorial_service import MemorialService

router = APIRouter(tags=["memorials"])


def _service(
    db: AsyncSession = Depends(get_db), settings: Settings = Depends(get_settings)
) -> MemorialService:
    """@brief MemorialService bound to the request session."""
    cid = uuid.UUID(settings.COMMUNITY_ID)
    return MemorialService(
        HouseholdRepository(db),
        UserRepository(db),
        TokenRepository(db),
        AuditRepository(db),
        CommunityRepository(db),
        cid,
        relations=build_relation_service(db, cid),
    )


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.put("/household/{member_id}/passed-on", response_model=HouseholdResponse)
async def set_passed_on(
    member_id: uuid.UUID,
    body: PassedOnBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    svc: MemorialService = Depends(_service),
) -> Any:
    """@brief Set or clear a household member's passed-on date (owner or admin)."""
    m = await svc.set_passed_on(member_id, user, body.passed_on)
    return await HouseholdService(HouseholdRepository(db), user.community_id).view(m, user)


@router.post("/admin/users/{user_id}/memorialize")
async def memorialize_user(
    user_id: uuid.UUID,
    body: PassedOnBody,
    request: Request,
    admin: User = Depends(require_role("admin")),
    svc: MemorialService = Depends(_service),
) -> dict[str, str]:
    """@brief Memorialize an account (admin)."""
    await svc.memorialize_user(user_id, admin, body.passed_on, _ip(request))
    return {"message": "User memorialized"}


@router.post("/admin/users/{user_id}/unmemorialize")
async def unmemorialize_user(
    user_id: uuid.UUID,
    request: Request,
    admin: User = Depends(require_role("admin")),
    svc: MemorialService = Depends(_service),
) -> dict[str, str]:
    """@brief Restore a memorialized account (admin)."""
    await svc.unmemorialize_user(user_id, admin, _ip(request))
    return {"message": "User restored"}
