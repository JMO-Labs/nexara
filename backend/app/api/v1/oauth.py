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
from typing import TYPE_CHECKING, Any, cast
from urllib.parse import urlencode

import httpx
import structlog
from fastapi import APIRouter, Cookie, Depends, Request, Response
from fastapi.responses import RedirectResponse
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.cookies import should_secure_cookie
from app.core.dependencies import get_db
from app.core.exceptions import AuthenticationError, SsoRefusedError
from app.core.i18n import _
from app.core.valkey import DB_CACHE, get_pool
from app.schemas.auth import LoginResponse
from app.schemas.oauth import OAuthExchangeRequest
from app.services.auth.signin_log import log_failure
from app.services.auth_service import AuthService
from app.services.oauth import sso_test_login
from app.services.oauth.claim_mapper import map_claims
from app.services.oauth.flow import OAuthFlow, apply_email_trust
from app.services.oauth.group_mapper import global_role_mappings, map_groups_to_role
from app.services.oauth.provider_manager import ProviderManager
from app.services.oauth.public_url import callback_url, public_base
from app.services.oauth.token_verifier import extract_claims, verify_id_token
from app.services.oauth.user_provisioner import OAuthAuthResult, UserProvisioner

if TYPE_CHECKING:
    from app.models.oauth_provider import OAuthProvider

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/oauth", tags=["oauth"])

OAUTH_STATE_COOKIE = "oauth_state"
OAUTH_VERIFIER_COOKIE = "oauth_verifier"
OAUTH_PROVIDER_COOKIE = "oauth_provider"
OAUTH_NONCE_COOKIE = "oauth_nonce"
COOKIE_MAX_AGE = 600
REFRESH_COOKIE = "refresh_token"
REFRESH_MAX_AGE = 30 * 24 * 3600


def _get_valkey_client(settings: Settings) -> Redis:
    """@brief Return Valkey client for cache DB (oauth exchange codes)."""
    return get_pool(settings, DB_CACHE)


def _set_refresh_cookie(response: Response, raw_token: str, settings: Settings) -> None:
    """@brief Set HttpOnly refresh token cookie."""
    response.set_cookie(
        REFRESH_COOKIE,
        raw_token,
        max_age=REFRESH_MAX_AGE,
        httponly=True,
        secure=should_secure_cookie(settings),
        samesite="lax",
        path="/api/v1/auth",
    )


def _set_oauth_cookies(
    response: Response,
    state: str,
    verifier: str,
    provider_slug: str,
    nonce: str | None,
    settings: Settings,
) -> None:
    """@brief Set OAuth state, verifier, provider (and nonce) cookies."""
    for name, value in (
        (OAUTH_STATE_COOKIE, state),
        (OAUTH_VERIFIER_COOKIE, verifier),
        (OAUTH_PROVIDER_COOKIE, provider_slug),
        (OAUTH_NONCE_COOKIE, nonce or ""),
    ):
        if not value:
            continue
        response.set_cookie(
            name,
            value,
            max_age=COOKIE_MAX_AGE,
            httponly=True,
            secure=should_secure_cookie(settings),
            samesite="lax",
        )


def _clear_oauth_cookies(response: Response) -> None:
    """@brief Clear OAuth cookies after callback."""
    for name in (
        OAUTH_STATE_COOKIE,
        OAUTH_VERIFIER_COOKIE,
        OAUTH_PROVIDER_COOKIE,
        OAUTH_NONCE_COOKIE,
    ):
        response.delete_cookie(name)


FAILED = "sso_failed"
"""@brief Generic error code for any non-refusal callback failure."""


def _failure_redirect(settings: Settings, path: str = "/login") -> RedirectResponse:
    """@brief Redirect the browser to a frontend page with ?error=sso_failed."""
    resp = RedirectResponse(url=f"{public_base(settings)}{path}?error={FAILED}", status_code=302)
    _clear_oauth_cookies(resp)
    return resp


async def _login_failed(
    db: AsyncSession, settings: Settings, request: Request, slug: str, reason: str, detail: str
) -> RedirectResponse:
    """
    @brief Roll back partial provisioning, log + record the failure, redirect to /login.

    @param reason Short machine reason (stored in signin_events; never echoed).
    @param detail Server-log-only detail.
    """
    await db.rollback()  # never commit a half-provisioned user
    logger.warning("sso_callback_failed", provider=slug, reason=reason, detail=detail[:300])
    await log_failure(settings, None, None, "sso", reason[:100], request)
    return _failure_redirect(settings)


async def _fetch_claims(
    provider: OAuthProvider, token_data: dict[str, Any], nonce: str | None
) -> dict[str, Any]:
    """@brief Verified ID token claims (OIDC) or userinfo claims (OAuth2)."""
    if provider.provider_type == "oidc" and token_data.get("id_token"):
        if not nonce:
            raise AuthenticationError(message=_("Missing OAuth session"))
        return await verify_id_token(token_data["id_token"], provider, nonce=nonce)
    if provider.userinfo_endpoint and token_data.get("access_token"):
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                provider.userinfo_endpoint,
                headers={"Authorization": f"Bearer {token_data['access_token']}"},
            )
            resp.raise_for_status()
            return cast(dict[str, Any], resp.json())
    raise AuthenticationError(message=_("OAuth response missing identity"))


async def _identity(
    provider: OAuthProvider, token_data: dict[str, Any], nonce: str | None
) -> tuple[dict[str, Any], OAuthAuthResult, str]:
    """@brief Claims, mapped identity and group-mapped community role."""
    claims = await _fetch_claims(provider, token_data, nonce)
    if isinstance(provider.claim_mapping, dict) and provider.claim_mapping:
        auth_result = map_claims(
            claims, provider.claim_mapping, provider.username_claim or "preferred_username"
        )
    else:
        auth_result = extract_claims(claims, provider)
    await apply_email_trust(provider, token_data, auth_result)
    role = map_groups_to_role(
        auth_result.groups or [],
        {**(provider.group_mappings or {}), **global_role_mappings(provider.claim_mapping)},
        provider.default_role or "member",
    )
    return claims, auth_result, role


async def _test_callback(
    ctx: dict[str, Any], code: str, db: AsyncSession, settings: Settings
) -> RedirectResponse:
    """
    @brief Finish an admin test login: verify and report, never provision.

    No user, link, membership, token or sign-in record is written. Any failure
    redirects the popup to /sso-test?error=sso_failed (details in the server log).
    """
    try:
        result_id = await _run_test_login(ctx, code, db, settings)
    except Exception as exc:  # noqa: BLE001 — the popup must never show raw JSON
        await db.rollback()
        logger.warning("sso_test_callback_failed", reason=type(exc).__name__, detail=str(exc))
        done = _failure_redirect(settings, "/sso-test")
    else:
        query = urlencode({"result": result_id})
        done = RedirectResponse(url=f"{public_base(settings)}/sso-test?{query}", status_code=302)
    done.delete_cookie(sso_test_login.BIND_COOKIE, path="/api/v1/oauth")
    return done


async def _run_test_login(
    ctx: dict[str, Any], code: str, db: AsyncSession, settings: Settings
) -> str:
    """@brief Exchange + verify for a test login; returns the stored result id."""
    community_id = uuid.UUID(settings.COMMUNITY_ID)
    provider = await sso_test_login.load_provider(db, community_id, ctx["provider_id"])
    if provider is None:
        raise AuthenticationError(message=_("OAuth provider not found"))
    token_data = await OAuthFlow().exchange_code(
        provider,
        code,
        ctx["verifier"],
        callback_url(settings, provider.slug),
        settings.SECRET_KEY,
    )
    claims, auth_result, role = await _identity(provider, token_data, ctx.get("nonce"))
    result = await sso_test_login.build_result(
        db, community_id, provider, claims, auth_result, role
    )
    valkey = _get_valkey_client(settings)
    return await sso_test_login.store_result(valkey, ctx["admin_id"], result)


@router.get("/{slug}/login")
async def oauth_login(
    slug: str,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    """
    @brief Redirect to OAuth provider authorization endpoint.

    Sets state, verifier, and provider cookies for callback validation. An
    unknown or disabled provider redirects to /login?error=sso_failed.
    """
    community_id = uuid.UUID(settings.COMMUNITY_ID)
    provider = await ProviderManager(db).get_provider(community_id, slug)
    if not provider or not provider.enabled:
        logger.info("sso_login_unknown_provider", provider=slug)
        return _failure_redirect(settings)

    redirect_uri = callback_url(settings, slug)
    nonce = secrets.token_urlsafe(32) if provider.provider_type == "oidc" else None
    url, state, verifier = OAuthFlow().build_authorize_url(provider, redirect_uri, nonce=nonce)
    redir = RedirectResponse(url=url, status_code=302)
    _set_oauth_cookies(redir, state, verifier, slug, nonce, settings)
    return redir


@router.get("/{slug}/callback")
async def oauth_callback(
    slug: str,
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    oauth_state: str | None = Cookie(None, alias=OAUTH_STATE_COOKIE),
    oauth_verifier: str | None = Cookie(None, alias=OAUTH_VERIFIER_COOKIE),
    oauth_provider: str | None = Cookie(None, alias=OAUTH_PROVIDER_COOKIE),
    oauth_nonce: str | None = Cookie(None, alias=OAUTH_NONCE_COOKIE),
    oauth_test_bind: str | None = Cookie(None, alias=sso_test_login.BIND_COOKIE),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    """
    @brief Handle OAuth callback: exchange code, provision user, redirect to frontend.

    Every outcome is a browser redirect: success -> /callback?code=, refusal ->
    /login?error=<code>, anything else -> /login?error=sso_failed.
    """
    if error or not code or not state:
        reason = f"idp_error:{error}" if error else "missing_code_or_state"
        return await _login_failed(db, settings, request, slug, reason, reason)
    if not oauth_state or not secrets.compare_digest(oauth_state, state):
        # Not this browser's login: maybe an admin test login (state kept server-side).
        try:
            ctx = await sso_test_login.consume_context(_get_valkey_client(settings), state)
        except Exception as exc:  # noqa: BLE001
            return await _login_failed(db, settings, request, slug, "state_lookup", str(exc))
        if (
            ctx is None
            or ctx.get("slug") != slug
            or not sso_test_login.binding_ok(ctx, oauth_test_bind)
        ):
            return await _login_failed(db, settings, request, slug, "invalid_state", "state")
        return await _test_callback(ctx, code, db, settings)
    if not oauth_verifier or oauth_provider != slug:
        return await _login_failed(db, settings, request, slug, "missing_session", "cookies")
    try:
        return await _complete_login(slug, code, oauth_verifier, oauth_nonce, request, db, settings)
    except Exception as exc:  # noqa: BLE001 — every failure becomes a redirect
        reason = f"callback:{type(exc).__name__}"
        return await _login_failed(db, settings, request, slug, reason, str(exc))


async def _complete_login(
    slug: str,
    code: str,
    verifier: str,
    nonce: str | None,
    request: Request,
    db: AsyncSession,
    settings: Settings,
) -> RedirectResponse:
    """@brief Exchange, verify and provision; refusals redirect with their code."""
    community_id = uuid.UUID(settings.COMMUNITY_ID)
    provider = await ProviderManager(db).get_provider(community_id, slug)
    if not provider or not provider.enabled:
        raise AuthenticationError(message=_("OAuth provider not found"))
    token_data = await OAuthFlow().exchange_code(
        provider, code, verifier, callback_url(settings, slug), settings.SECRET_KEY
    )
    _claims, auth_result, role = await _identity(provider, token_data, nonce)
    frontend_url = public_base(settings)
    provisioner = UserProvisioner(db, community_id)
    try:
        user = await provisioner.provision_user(auth_result, provider, role)
    except SsoRefusedError as exc:
        # Return normally so the session commits any token revocation.
        logger.info("sso_refused", provider=slug, code=exc.code)
        await log_failure(
            settings, None, auth_result.email, "sso", exc.code, request, user_id=exc.user_id
        )
        query = urlencode({"error": exc.code, "provider": provider.display_name})
        refused = RedirectResponse(url=f"{frontend_url}/login?{query}", status_code=302)
        _clear_oauth_cookies(refused)
        return refused

    exchange_code = secrets.token_urlsafe(48)
    payload = json.dumps(
        {
            "user_id": str(user.id),
            "provider_slug": slug,
            # First link to an account with a local factor: created only after 2FA.
            "pending_link": (
                provisioner.pending_link if isinstance(provisioner.pending_link, dict) else None
            ),
        }
    )
    await _get_valkey_client(settings).setex(f"oauth_exchange:{exchange_code}", 60, payload)
    done = RedirectResponse(url=f"{frontend_url}/callback?code={exchange_code}", status_code=302)
    _clear_oauth_cookies(done)
    return done


@router.post("/exchange", response_model=LoginResponse)
async def oauth_exchange(
    request: Request,
    body: OAuthExchangeRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> LoginResponse:
    """
    @brief Exchange OAuth callback code (single use, atomic GETDEL) for Nexara JWTs.
    """
    raw = await _get_valkey_client(settings).getdel(f"oauth_exchange:{body.code}")
    if not raw:
        raise AuthenticationError(message=_("Invalid or expired code"))
    result = await AuthService(db, settings).exchange_sso(json.loads(raw), request=request)
    if result.get("requires_2fa"):
        return LoginResponse(
            requires_2fa=True,
            two_factor_token=result["two_factor_token"],
            two_factor_methods=result.get("two_factor_methods"),
        )
    _set_refresh_cookie(response, result["raw_refresh_token"], settings)
    return LoginResponse(
        access_token=result["access_token"],
        expires_in=result["expires_in"],
    )
