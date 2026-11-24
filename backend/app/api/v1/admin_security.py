"""
@file admin_security.py
@brief Admin: reset a member's 2FA and set the community 2FA policy.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from app.core.dependencies import require_role
from app.core.deps_two_factor import get_admin_security_service
from app.schemas.common import MessageResponse
from app.schemas.two_factor import SecurityPolicy
from app.services.admin_security_service import AdminSecurityService

router = APIRouter(
    prefix="/admin",
    tags=["admin-security"],
    dependencies=[Depends(require_role("admin"))],
)


@router.post("/users/{user_id}/reset-2fa", response_model=MessageResponse)
async def reset_2fa(
    user_id: uuid.UUID, svc: AdminSecurityService = Depends(get_admin_security_service)
) -> MessageResponse:
    """@brief Clear a member's TOTP, recovery codes and passkeys."""
    await svc.reset_2fa(user_id)
    return MessageResponse(message="2FA reset")


@router.get("/security", response_model=SecurityPolicy)
async def get_security(
    svc: AdminSecurityService = Depends(get_admin_security_service),
) -> SecurityPolicy:
    """@brief Read the community 2FA policy."""
    return SecurityPolicy(require_2fa=await svc.get_policy())


@router.put("/security", response_model=SecurityPolicy)
async def put_security(
    body: SecurityPolicy, svc: AdminSecurityService = Depends(get_admin_security_service)
) -> SecurityPolicy:
    """@brief Set the community 2FA policy."""
    return SecurityPolicy(require_2fa=await svc.set_policy(body.require_2fa))
