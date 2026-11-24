"""
@file auth_2fa.py
@brief /auth/2fa/*: TOTP lifecycle, recovery codes, status, and the login step.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import get_db
from app.core.deps_two_factor import get_two_factor_service
from app.core.rate_limit import limiter
from app.schemas.auth import (
    LoginResponse,
    TwoFactorEnrollResponse,
    TwoFactorLoginRequest,
    TwoFactorVerifyRequest,
    TwoFactorVerifyResponse,
)
from app.schemas.common import MessageResponse
from app.schemas.two_factor import CodeBody, DisableBody, RecoveryCodes, TwoFactorStatus
from app.services.auth.two_factor import TwoFactorService
from app.services.auth_service import AuthService

router = APIRouter(prefix="/2fa")


@router.get("/status", response_model=TwoFactorStatus)
async def status(svc: TwoFactorService = Depends(get_two_factor_service)) -> Any:
    """@brief TOTP / passkey / recovery state and whether 2FA is still required."""
    return await svc.status()


@router.post("/totp/start", response_model=TwoFactorEnrollResponse)
async def totp_start(svc: TwoFactorService = Depends(get_two_factor_service)) -> Any:
    """@brief Begin TOTP enrolment (secret stays pending until confirmed)."""
    return await svc.start()


@router.post("/totp/confirm", response_model=RecoveryCodes)
async def totp_confirm(
    body: CodeBody, svc: TwoFactorService = Depends(get_two_factor_service)
) -> RecoveryCodes:
    """@brief Enable TOTP with the first code; returns 10 recovery codes."""
    return RecoveryCodes(recovery_codes=await svc.confirm(body.code))


@router.post("/totp/disable", response_model=MessageResponse)
async def totp_disable(
    body: DisableBody, svc: TwoFactorService = Depends(get_two_factor_service)
) -> MessageResponse:
    """@brief Disable TOTP; needs the password or a valid code."""
    await svc.disable(body.password, body.code)
    return MessageResponse(message="2FA disabled")


@router.post("/recovery/regenerate", response_model=RecoveryCodes)
async def recovery_regenerate(
    body: CodeBody, svc: TwoFactorService = Depends(get_two_factor_service)
) -> RecoveryCodes:
    """@brief Replace the recovery codes (needs a valid code)."""
    return RecoveryCodes(recovery_codes=await svc.regenerate(body.code))


# ponytail: alias, remove in PR3 Task 4
@router.post("/enroll", response_model=TwoFactorEnrollResponse)
async def enroll_alias(svc: TwoFactorService = Depends(get_two_factor_service)) -> Any:
    """@brief Alias of ``/totp/start``."""
    return await svc.start()


# ponytail: alias, remove in PR3 Task 4
@router.post("/verify", response_model=TwoFactorVerifyResponse)
async def verify_alias(
    body: TwoFactorVerifyRequest, svc: TwoFactorService = Depends(get_two_factor_service)
) -> Any:
    """@brief Alias of ``/totp/confirm`` (old response shape)."""
    return TwoFactorVerifyResponse(backup_codes=await svc.confirm(body.code))


@router.post("/login", response_model=LoginResponse)
@limiter.limit("10/minute")
async def login_2fa(
    request: Request,
    body: TwoFactorLoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Any:
    """@brief Complete a 2FA-pending login with a TOTP code."""
    from app.api.v1.auth import _set_refresh_cookie

    svc = AuthService(db, settings)
    result = await svc.verify_2fa_login(
        two_factor_token=body.two_factor_token, code=body.code, request=request
    )
    _set_refresh_cookie(response, result["raw_refresh_token"], settings)
    return LoginResponse(access_token=result["access_token"], expires_in=result["expires_in"])
