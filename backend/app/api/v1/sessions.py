"""
@file sessions.py
@brief Member device list: GET/DELETE /auth/sessions, POST /auth/sessions/revoke-others.

Mounted under /auth so the path-scoped refresh cookie (/api/v1/auth) is sent.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Cookie, Depends

from app.core.deps_signins import get_session_service
from app.schemas.common import MessageResponse
from app.schemas.signin import SessionOut
from app.services.session_service import SessionService

router = APIRouter(prefix="/auth/sessions", tags=["sessions"])

REFRESH_COOKIE = "refresh_token"


@router.get("", response_model=list[SessionOut])
async def list_sessions(
    refresh_token: str | None = Cookie(None, alias=REFRESH_COOKIE),
    svc: SessionService = Depends(get_session_service),
) -> list[SessionOut]:
    """@brief Devices signed in as the current user."""
    return await svc.list(refresh_token)


@router.post("/revoke-others", response_model=MessageResponse)
async def revoke_others(
    refresh_token: str | None = Cookie(None, alias=REFRESH_COOKIE),
    svc: SessionService = Depends(get_session_service),
) -> MessageResponse:
    """@brief Sign out all devices except this one."""
    await svc.revoke_others(refresh_token)
    return MessageResponse(message="ok")


@router.delete("/{family_id}", response_model=MessageResponse)
async def revoke_session(
    family_id: uuid.UUID, svc: SessionService = Depends(get_session_service)
) -> MessageResponse:
    """@brief Sign out one device (404 if not yours)."""
    await svc.revoke(family_id)
    return MessageResponse(message="ok")
