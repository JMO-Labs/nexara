"""
@file presence.py
@brief POST /api/v1/presence: batch online status lookup.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.repositories.presence_repo import PresenceRepository
from app.schemas.presence import PresenceRequest, PresenceResponse
from app.services.presence_service import PresenceService

router = APIRouter(prefix="/presence", tags=["presence"])


@router.post("", response_model=PresenceResponse)
async def lookup_presence(
    body: PresenceRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PresenceResponse:
    """@brief Return which of the requested users are online (privacy applied)."""
    service = PresenceService(PresenceRepository(db), user.community_id)
    return await service.lookup(user.id, body.user_ids)
