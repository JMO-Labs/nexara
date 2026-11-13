"""
@file auth_password_reset.py
@brief Password reset route handlers (included in the auth router).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import get_db
from app.core.i18n import _
from app.schemas.auth import PasswordResetConfirmPayload, PasswordResetRequestPayload
from app.schemas.common import MessageResponse
from app.services.auth_service import AuthService

router = APIRouter(tags=["auth"])


@router.post("/password-reset/request", response_model=MessageResponse)
async def request_password_reset(
    body: PasswordResetRequestPayload,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Any:
    """
    @brief Request a password reset email.

    Always returns the same response to prevent account enumeration.
    """
    svc = AuthService(db, settings)
    await svc.request_password_reset(body.email)
    return MessageResponse(message=_("If that email is registered, a reset link has been sent"))


@router.post("/password-reset/confirm", response_model=MessageResponse)
async def confirm_password_reset(
    body: PasswordResetConfirmPayload,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Any:
    """@brief Apply a new password using a valid reset token."""
    svc = AuthService(db, settings)
    await svc.reset_password(body.token, body.new_password)
    return MessageResponse(message=_("Password has been reset successfully"))
