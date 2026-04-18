"""
@file auth_magic_link.py
@brief Magic link (passwordless login) route handlers.

Route handlers validate input, delegate to AuthService, and format responses.
Included in the main auth router at prefix /magic-link.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import get_db
from app.core.i18n import _
from app.core.rate_limit import limiter
from app.schemas.auth import LoginResponse, MagicLinkRequestPayload
from app.schemas.common import MessageResponse
from app.services.auth_service import AuthService

router = APIRouter(tags=["auth"])


def _set_refresh_cookie(response: Response, raw_token: str, settings: Settings) -> None:
    """
    @brief Set the HttpOnly refresh token cookie on the response.

    @param response FastAPI response object.
    @param raw_token Raw opaque refresh token.
    @param settings Application settings (used to derive Secure flag).
    """
    from app.api.v1.auth import COOKIE_MAX_AGE, REFRESH_COOKIE, _should_secure_cookie

    response.set_cookie(
        REFRESH_COOKIE,
        raw_token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        secure=_should_secure_cookie(settings),
        samesite="lax",
        path="/api/v1/auth",
    )


@router.post("/request", response_model=MessageResponse)
@limiter.limit("10/minute")
async def request_magic_link(
    request: Request,
    body: MagicLinkRequestPayload,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Any:
    """
    @brief Request a magic link for passwordless login.

    Always returns the same response to prevent account enumeration.
    Rate limited.
    """
    svc = AuthService(db, settings)
    await svc.request_magic_link(body.email)
    return MessageResponse(message=_("If account exists, a magic link has been sent"))


@router.get("/verify", response_model=LoginResponse)
async def verify_magic_link(
    token: str,
    response: Response,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Any:
    """@brief Verify a magic link token and return JWT session."""
    svc = AuthService(db, settings)
    result = await svc.verify_magic_link(token)
    _set_refresh_cookie(response, result["raw_refresh_token"], settings)
    return LoginResponse(
        access_token=result["access_token"],
        expires_in=result["expires_in"],
    )
