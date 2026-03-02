"""
@file auth.py
@brief Authentication route handlers: login, register, refresh, logout, 2FA, OIDC, password reset.

Route handlers validate input, delegate to services, and format responses.
No business logic lives here.
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from fastapi import APIRouter, Cookie, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import get_current_user, get_db, get_optional_user
from app.core.i18n import _
from app.core.security import get_jwks
from app.models.user import User
from app.repositories.notification_repo import NotificationRepository
from app.repositories.settings_repo import SettingsRepository
from app.schemas.auth import (
    AuthConfigResponse,
    LoginRequest,
    LoginResponse,
    LogoutResponse,
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
from app.services.notification_service import NotificationService
from app.services.realtime.event_bus import event_bus

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "refresh_token"
COOKIE_MAX_AGE = 30 * 24 * 3600  # 30 days


def _should_secure_cookie(settings: Settings) -> bool:
    """@brief Return True if cookies should use the Secure flag (origins are HTTPS)."""
    origins = settings.allowed_origins_list
    return all(o.startswith("https://") for o in origins) if origins else True


def _set_refresh_cookie(response: Response, raw_token: str, settings: Settings) -> None:
    """
    @brief Set the HttpOnly refresh token cookie on the response.

    @param response FastAPI response object.
    @param raw_token Raw opaque refresh token.
    @param settings Application settings (used to derive Secure flag).
    """
    response.set_cookie(
        REFRESH_COOKIE,
        raw_token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        secure=_should_secure_cookie(settings),
        samesite="lax",
        path="/api/v1/auth",
    )


def _clear_refresh_cookie(response: Response) -> None:
    """
    @brief Delete the refresh token cookie.

    @param response FastAPI response object.
    """
    response.delete_cookie(REFRESH_COOKIE, path="/api/v1/auth")


# ── Public config ────────────────────────────────────────────────────────


@router.get("/config", response_model=AuthConfigResponse)
async def get_auth_config(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AuthConfigResponse:
    """
    @brief Return public auth configuration for the login page.

    No authentication required. Used by the frontend to conditionally
    show OIDC SSO button, local login form, and registration link.
    """
    from app.schemas.auth import OAuthProviderListItem
    from app.services.oauth.provider_manager import ProviderManager

    oauth_providers: list[OAuthProviderListItem] = []
    try:
        community_id = uuid.UUID(settings.COMMUNITY_ID)
        manager = ProviderManager(db)
        providers = await manager.get_enabled_providers(community_id)
        oauth_providers = [
            OAuthProviderListItem(
                slug=p.slug,
                display_name=p.display_name,
                icon_url=p.icon_url,
            )
            for p in providers
        ]
    except Exception:
        logger.warning("oauth_providers_unavailable", exc_info=True)

    oidc_enabled = len(oauth_providers) > 0
    return AuthConfigResponse(
        oidc_enabled=oidc_enabled,
        registration_enabled=settings.ENABLE_REGISTRATION,
        local_auth_enabled=True,
        oauth_providers=oauth_providers,
    )


# ── Registration & Login ─────────────────────────────────────────────────


@router.post("/register", response_model=LoginResponse, status_code=201)
async def register(
    body: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Any:
    """@brief Create a new user account via local registration."""
    import uuid as _uuid

    notification_svc = NotificationService(
        notification_repo=NotificationRepository(db),
        settings_repo=SettingsRepository(db),
        community_id=_uuid.UUID(settings.COMMUNITY_ID),
        event_bus=event_bus,
    )
    svc = AuthService(db, settings, notification_service=notification_svc)
    result = await svc.register(
        email=body.email,
        username=body.username,
        password=body.password,
        display_name=body.display_name,
        invite_token=body.invite_token,
    )
    _set_refresh_cookie(response, result["raw_refresh_token"], settings)
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

    _set_refresh_cookie(response, result["raw_refresh_token"], settings)
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
    _set_refresh_cookie(response, result["raw_refresh_token"], settings)
    return LoginResponse(
        access_token=result["access_token"],
        expires_in=result["expires_in"],
    )


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    response: Response,
    refresh_token: str | None = Cookie(None, alias=REFRESH_COOKIE),
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Any:
    """
    @brief Revoke the refresh token and clear the cookie.

    If the user has an OAuth link to a provider with end_session_endpoint,
    returns end_session_url for RP-initiated logout.
    """
    if refresh_token:
        svc = AuthService(db, settings)
        await svc.logout(refresh_token)
    _clear_refresh_cookie(response)

    end_session_url: str | None = None
    if user:
        from app.repositories.oauth_repo import (
            OAuthProviderRepository,
            UserOAuthLinkRepository,
        )

        link_repo = UserOAuthLinkRepository(db)
        provider_repo = OAuthProviderRepository(db)
        links = await link_repo.find_links_for_user(user.id)
        for link in links:
            provider = await provider_repo.get_by_id(link.provider_id, None)
            if provider and provider.end_session_endpoint:
                end_session_url = provider.end_session_endpoint
                break

    return LogoutResponse(
        message=_("Logged out successfully"),
        end_session_url=end_session_url,
    )


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
    _set_refresh_cookie(response, result["raw_refresh_token"], settings)
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


# ── OIDC (deprecated, redirects to multi-provider OAuth) ───────────────────


@router.get("/oidc/login", deprecated=True)
async def oidc_login_deprecated(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Any:
    """
    @brief Deprecated — redirects to /oauth/{slug}/login for the default provider.
    """
    from starlette.responses import RedirectResponse

    from app.core.exceptions import AuthenticationError
    from app.services.oauth.provider_manager import ProviderManager

    manager = ProviderManager(db)
    community_id = uuid.UUID(settings.COMMUNITY_ID)
    providers = await manager.get_enabled_providers(community_id)

    if not providers:
        raise AuthenticationError(message=_("No OAuth providers configured"))

    slug = providers[0].slug
    return RedirectResponse(url=f"/api/v1/oauth/{slug}/login", status_code=307)


@router.get("/oidc/callback", deprecated=True)
async def oidc_callback_deprecated(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    oidc_state: str | None = Cookie(None),
) -> Any:
    """
    @brief Deprecated — redirects to /oauth/{slug}/callback for the default provider.
    """
    from starlette.responses import RedirectResponse

    from app.core.exceptions import AuthenticationError
    from app.services.oauth.provider_manager import ProviderManager

    manager = ProviderManager(db)
    community_id = uuid.UUID(settings.COMMUNITY_ID)
    providers = await manager.get_enabled_providers(community_id)

    if not providers:
        raise AuthenticationError(message=_("No OAuth providers configured"))

    slug = providers[0].slug
    return RedirectResponse(
        url=f"/api/v1/oauth/{slug}/callback?code={code}&state={state}",
        status_code=307,
    )


# ── JWKS ─────────────────────────────────────────────────────────────────


@router.get("/.well-known/jwks.json")
async def jwks(settings: Settings = Depends(get_settings)) -> Any:
    """@brief Serve the JSON Web Key Set for JWT verification by external services."""
    return get_jwks(settings)
