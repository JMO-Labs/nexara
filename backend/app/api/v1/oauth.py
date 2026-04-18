"""
@file oauth.py
@brief Public OAuth2/OIDC route handlers: login, callback, exchange.

Handles multi-provider OAuth flows with PKCE, state validation,
and exchange code for JWT tokens.
"""

from __future__ import annotations

import json
import secrets
import uuid
from typing import Any

import httpx
import structlog
from fastapi import APIRouter, Cookie, Depends, Request, Response
from fastapi.responses import RedirectResponse
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import get_db
from app.core.exceptions import AuthenticationError
from app.core.i18n import _
from app.core.valkey import DB_CACHE, get_pool
from app.repositories.user_repo import UserRepository
from app.schemas.auth import LoginResponse
from app.schemas.oauth import OAuthExchangeRequest
from app.services.auth_service import AuthService
from app.services.oauth.flow import OAuthFlow
from app.services.oauth.group_mapper import map_groups_to_role
from app.services.oauth.provider_manager import ProviderManager
from app.services.oauth.token_verifier import extract_claims, verify_id_token
from app.services.oauth.user_provisioner import UserProvisioner

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/oauth", tags=["oauth"])

OAUTH_STATE_COOKIE = "oauth_state"
OAUTH_VERIFIER_COOKIE = "oauth_verifier"
OAUTH_PROVIDER_COOKIE = "oauth_provider"
COOKIE_MAX_AGE = 600
REFRESH_COOKIE = "refresh_token"
REFRESH_MAX_AGE = 30 * 24 * 3600


def _get_valkey_client(settings: Settings) -> Redis:
    """@brief Return Valkey client for cache DB (oauth exchange codes)."""
    return get_pool(settings, DB_CACHE)


def _should_secure_cookie(settings: Settings) -> bool:
    """@brief Return True if cookies should use the Secure flag (origins are HTTPS)."""
    origins = settings.allowed_origins_list or []
    return all(o.startswith("https://") for o in origins) if origins else True


def _set_refresh_cookie(response: Response, raw_token: str, settings: Settings) -> None:
    """@brief Set HttpOnly refresh token cookie."""
    response.set_cookie(
        REFRESH_COOKIE,
        raw_token,
        max_age=REFRESH_MAX_AGE,
        httponly=True,
        secure=_should_secure_cookie(settings),
        samesite="lax",
        path="/api/v1/auth",
    )


def _set_oauth_cookies(
    response: Response,
    state: str,
    verifier: str,
    provider_slug: str,
) -> None:
    """@brief Set OAuth state, verifier, and provider cookies."""
    for name, value in (
        (OAUTH_STATE_COOKIE, state),
        (OAUTH_VERIFIER_COOKIE, verifier),
        (OAUTH_PROVIDER_COOKIE, provider_slug),
    ):
        response.set_cookie(
            name,
            value,
            max_age=COOKIE_MAX_AGE,
            httponly=True,
            samesite="lax",
        )


def _clear_oauth_cookies(response: Response) -> None:
    """@brief Clear OAuth cookies after callback."""
    for name in (OAUTH_STATE_COOKIE, OAUTH_VERIFIER_COOKIE, OAUTH_PROVIDER_COOKIE):
        response.delete_cookie(name)


def _build_redirect_uri(request: Request, slug: str, settings: Settings) -> str:
    """@brief Build callback URL using the public frontend origin.

    Uses ALLOWED_ORIGINS so the callback goes through the frontend proxy,
    ensuring cookies set during login are present on the callback request.
    """
    origins = settings.allowed_origins_list
    base = origins[0] if origins else str(request.base_url).rstrip("/")
    return f"{base}/api/v1/oauth/{slug}/callback"


@router.get("/{slug}/login")
async def oauth_login(
    slug: str,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    """
    @brief Redirect to OAuth provider authorization endpoint.

    Sets state, verifier, and provider cookies for callback validation.
    """
    community_id = uuid.UUID(settings.COMMUNITY_ID)
    manager = ProviderManager(db)
    provider = await manager.get_provider(community_id, slug)
    if not provider or not provider.enabled:
        raise AuthenticationError(message=_("OAuth provider not found or disabled"))

    redirect_uri = _build_redirect_uri(request, slug, settings)
    flow = OAuthFlow()
    url, state, verifier = flow.build_authorize_url(provider, redirect_uri)
    redir = RedirectResponse(url=url, status_code=302)
    _set_oauth_cookies(redir, state, verifier, slug)
    return redir


@router.get("/{slug}/callback")
async def oauth_callback(
    slug: str,
    code: str,
    state: str,
    request: Request,
    response: Response,
    oauth_state: str | None = Cookie(None, alias=OAUTH_STATE_COOKIE),
    oauth_verifier: str | None = Cookie(None, alias=OAUTH_VERIFIER_COOKIE),
    oauth_provider: str | None = Cookie(None, alias=OAUTH_PROVIDER_COOKIE),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    """
    @brief Handle OAuth callback: exchange code, provision user, redirect to frontend.
    """
    if not oauth_state or not secrets.compare_digest(oauth_state, state):
        raise AuthenticationError(message=_("Invalid OAuth state"))
    if not oauth_verifier or oauth_provider != slug:
        raise AuthenticationError(message=_("Missing OAuth session"))

    community_id = uuid.UUID(settings.COMMUNITY_ID)
    manager = ProviderManager(db)
    provider = await manager.get_provider(community_id, slug)
    if not provider or not provider.enabled:
        raise AuthenticationError(message=_("OAuth provider not found"))

    redirect_uri = _build_redirect_uri(request, slug, settings)
    flow = OAuthFlow()
    token_data = await flow.exchange_code(
        provider, code, oauth_verifier, redirect_uri, settings.SECRET_KEY
    )

    claims: dict[str, Any]
    if provider.provider_type == "oidc" and token_data.get("id_token"):
        claims = await verify_id_token(token_data["id_token"], provider)
    elif provider.userinfo_endpoint and token_data.get("access_token"):
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                provider.userinfo_endpoint,
                headers={"Authorization": f"Bearer {token_data['access_token']}"},
            )
            resp.raise_for_status()
            claims = resp.json()
    else:
        raise AuthenticationError(message=_("OAuth response missing identity"))

    auth_result = extract_claims(claims, provider)
    role = map_groups_to_role(
        auth_result.groups or [],
        provider.group_mappings or {},
        provider.default_role or "member",
    )
    provisioner = UserProvisioner(db, community_id)
    user = await provisioner.provision_user(auth_result, provider, role)

    exchange_code = secrets.token_urlsafe(48)
    valkey = _get_valkey_client(settings)
    payload = json.dumps({"user_id": str(user.id), "provider_slug": slug})
    await valkey.setex(f"oauth_exchange:{exchange_code}", 60, payload)

    _clear_oauth_cookies(response)
    origins = settings.allowed_origins_list
    frontend_url = origins[0] if origins else str(request.base_url).rstrip("/")
    redirect_url = f"{frontend_url}/auth/callback?code={exchange_code}"
    return RedirectResponse(url=redirect_url, status_code=302)


@router.post("/exchange", response_model=LoginResponse)
async def oauth_exchange(
    body: OAuthExchangeRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> LoginResponse:
    """
    @brief Exchange OAuth callback code for Nexara JWT tokens.
    """
    valkey = _get_valkey_client(settings)
    raw = await valkey.get(f"oauth_exchange:{body.code}")
    if not raw:
        raise AuthenticationError(message=_("Invalid or expired code"))
    await valkey.delete(f"oauth_exchange:{body.code}")

    data = json.loads(raw)
    user_id_str = data.get("user_id")
    if not user_id_str:
        raise AuthenticationError(message=_("Invalid or expired code"))

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(uuid.UUID(user_id_str))
    if not user or not user.is_active:
        raise AuthenticationError(message=_("User not found or deactivated"))

    auth_svc = AuthService(db, settings)
    result = await auth_svc._issue_tokens(user)
    _set_refresh_cookie(response, result["raw_refresh_token"], settings)
    return LoginResponse(
        access_token=result["access_token"],
        expires_in=result["expires_in"],
    )
