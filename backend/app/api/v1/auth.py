"""
@file auth.py
@brief Authentication route handlers: login, register, refresh, logout, 2FA, OIDC, password reset.

Route handlers validate input, delegate to services, and format responses.
No business logic lives here.
"""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, Cookie, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import get_current_user, get_db
from app.core.i18n import _
from app.core.security import get_jwks
from app.models.user import User
from app.schemas.auth import (
    InviteCreateRequest,
    InviteResponse,
    LoginRequest,
    LoginResponse,
    PasswordResetConfirmPayload,
    PasswordResetRequestPayload,
    RegisterRequest,
    TwoFactorEnrollResponse,
    TwoFactorLoginRequest,
    TwoFactorVerifyRequest,
    TwoFactorVerifyResponse,
)
from app.schemas.common import MessageResponse
from app.services.auth_service import AuthService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "refresh_token"
COOKIE_MAX_AGE = 30 * 24 * 3600  # 30 days


def _set_refresh_cookie(response: Response, raw_token: str) -> None:
    """@brief Set the HttpOnly refresh token cookie on the response."""
    response.set_cookie(
        REFRESH_COOKIE,
        raw_token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/api/v1/auth",
    )


def _clear_refresh_cookie(response: Response) -> None:
    """@brief Delete the refresh token cookie."""
    response.delete_cookie(REFRESH_COOKIE, path="/api/v1/auth")


# ── Registration & Login ─────────────────────────────────────────────────


@router.post("/register", response_model=LoginResponse, status_code=201)
async def register(
    body: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Any:
    """@brief Create a new user account via local registration."""
    svc = AuthService(db, settings)
    result = await svc.register(
        email=body.email,
        username=body.username,
        password=body.password,
        display_name=body.display_name,
        invite_token=body.invite_token,
    )
    _set_refresh_cookie(response, result["raw_refresh_token"])
    return LoginResponse(
        access_token=result["access_token"],
        expires_in=result["expires_in"],
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Any:
    """@brief Authenticate with email and password."""
    svc = AuthService(db, settings)
    result = await svc.login(email=body.email, password=body.password)

    if result.get("requires_2fa"):
        return LoginResponse(
            requires_2fa=True,
            two_factor_token=result["two_factor_token"],
        )

    _set_refresh_cookie(response, result["raw_refresh_token"])
    return LoginResponse(
        access_token=result["access_token"],
        expires_in=result["expires_in"],
    )


# ── Token management ─────────────────────────────────────────────────────


@router.post("/refresh", response_model=LoginResponse)
async def refresh(
    request: Request,
    response: Response,
    refresh_token: str | None = Cookie(None, alias=REFRESH_COOKIE),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Any:
    """@brief Rotate the refresh token and issue a new access token."""
    if not refresh_token:
        from app.core.exceptions import AuthenticationError
        raise AuthenticationError(message=_("Refresh token missing"))

    svc = AuthService(db, settings)
    result = await svc.refresh(
        refresh_token,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    _set_refresh_cookie(response, result["raw_refresh_token"])
    return LoginResponse(
        access_token=result["access_token"],
        expires_in=result["expires_in"],
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    response: Response,
    refresh_token: str | None = Cookie(None, alias=REFRESH_COOKIE),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Any:
    """@brief Revoke the refresh token and clear the cookie."""
    if refresh_token:
        svc = AuthService(db, settings)
        await svc.logout(refresh_token)
    _clear_refresh_cookie(response)
    return MessageResponse(message=_("Logged out successfully"))


# ── Two-Factor Authentication ────────────────────────────────────────────


@router.post("/2fa/enroll", response_model=TwoFactorEnrollResponse)
async def enroll_2fa(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Any:
    """@brief Start 2FA enrollment (returns TOTP secret + QR URI)."""
    svc = AuthService(db, settings)
    return await svc.enroll_2fa(user)


@router.post("/2fa/verify", response_model=TwoFactorVerifyResponse)
async def verify_2fa_enrollment(
    body: TwoFactorVerifyRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Any:
    """@brief Complete 2FA enrollment by verifying the first TOTP code."""
    svc = AuthService(db, settings)
    codes = await svc.verify_2fa_enrollment(user, body.code)
    return TwoFactorVerifyResponse(backup_codes=codes)


@router.post("/2fa/login", response_model=LoginResponse)
async def login_2fa(
    body: TwoFactorLoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Any:
    """@brief Complete a 2FA-pending login with a TOTP code."""
    svc = AuthService(db, settings)
    result = await svc.verify_2fa_login(
        two_factor_token=body.two_factor_token,
        code=body.code,
    )
    _set_refresh_cookie(response, result["raw_refresh_token"])
    return LoginResponse(
        access_token=result["access_token"],
        expires_in=result["expires_in"],
    )


# ── Password Reset ───────────────────────────────────────────────────────


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


# ── OIDC ─────────────────────────────────────────────────────────────────


@router.get("/oidc/login")
async def oidc_login(
    response: Response,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Any:
    """@brief Redirect to the OIDC provider's authorization endpoint."""
    from app.services.oidc_service import OIDCService

    svc = OIDCService(db, settings)
    url, state, verifier = svc.build_authorize_url()
    response.set_cookie("oidc_state", state, max_age=600, httponly=True, samesite="lax")
    response.set_cookie("oidc_verifier", verifier, max_age=600, httponly=True, samesite="lax")
    from starlette.responses import RedirectResponse
    return RedirectResponse(url=url, status_code=302)


@router.get("/oidc/callback", response_model=LoginResponse)
async def oidc_callback(
    code: str,
    state: str,
    response: Response,
    oidc_state: str | None = Cookie(None),
    oidc_verifier: str | None = Cookie(None),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Any:
    """@brief Handle the OIDC provider callback after user authorization."""
    import secrets

    from app.core.exceptions import AuthenticationError
    from app.services.oidc_service import OIDCService

    if not oidc_state or not secrets.compare_digest(oidc_state, state):
        raise AuthenticationError(message=_("Invalid OIDC state"))
    if not oidc_verifier:
        raise AuthenticationError(message=_("Missing OIDC code verifier"))

    svc = OIDCService(db, settings)
    result = await svc.handle_callback(code, oidc_verifier)

    response.delete_cookie("oidc_state")
    response.delete_cookie("oidc_verifier")
    _set_refresh_cookie(response, result["raw_refresh_token"])
    return LoginResponse(
        access_token=result["access_token"],
        expires_in=result["expires_in"],
    )


# ── JWKS ─────────────────────────────────────────────────────────────────


@router.get("/.well-known/jwks.json")
async def jwks(settings: Settings = Depends(get_settings)) -> Any:
    """@brief Serve the JSON Web Key Set for JWT verification by external services."""
    return get_jwks(settings)
