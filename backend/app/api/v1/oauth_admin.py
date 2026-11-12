"""
@file oauth_admin.py
@brief Admin endpoints for generic OIDC providers (register via discovery, test).
"""

from __future__ import annotations

import uuid

import httpx
import structlog
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.admin_oauth import _client_ip, _community_id
from app.core.config import Settings, get_settings
from app.core.dependencies import get_db, require_role
from app.core.encryption import derive_fernet_key, encrypt_secret
from app.core.exceptions import AppError, NotFoundError
from app.core.i18n import _
from app.models.oauth_provider import OAuthProvider
from app.models.user import User
from app.repositories.audit_repo import AuditRepository
from app.repositories.oauth_repo import OAuthProviderRepository
from app.schemas.oauth import OAuthProviderResponse, OIDCProviderCreate, OIDCTestResult
from app.services.oauth.discovery import fetch_discovery

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/admin/oauth", tags=["admin-oauth"])


@router.post("/providers/oidc", response_model=OAuthProviderResponse, status_code=201)
async def create_oidc_provider(
    body: OIDCProviderCreate,
    request: Request,
    user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    community_id: uuid.UUID = Depends(_community_id),
) -> OAuthProviderResponse:
    """@brief Register an OIDC provider from its discovery URL."""
    try:
        doc = await fetch_discovery(body.discovery_url.strip(), settings.OIDC_HTTP_TIMEOUT)
    except (ValueError, httpx.HTTPError) as exc:
        raise AppError(code="invalid_discovery", message=str(exc), status_code=422) from exc

    provider = OAuthProvider(
        community_id=community_id,
        slug=body.slug,
        display_name=body.display_name,
        provider_type="oidc",
        client_id=body.client_id,
        client_secret_encrypted=encrypt_secret(
            body.client_secret, derive_fernet_key(settings.SECRET_KEY)
        ),
        issuer=doc["issuer"],
        discovery_url=body.discovery_url.strip(),
        scopes=body.scopes,
        claim_mapping=body.claim_mapping,
        authorization_endpoint=doc["authorization_endpoint"],
        token_endpoint=doc["token_endpoint"],
        userinfo_endpoint=doc.get("userinfo_endpoint"),
        jwks_uri=doc.get("jwks_uri"),
        end_session_endpoint=doc.get("end_session_endpoint"),
    )
    provider = await OAuthProviderRepository(db).create(provider)
    await AuditRepository(db).append(
        actor_id=user.id,
        action="oauth.provider.created",
        target_type="oauth_provider",
        target_id=provider.id,
        extra_data={"slug": provider.slug, "type": "oidc"},
        ip_address=_client_ip(request),
    )
    return OAuthProviderResponse.model_validate(provider)


@router.post("/providers/{provider_id}/test", response_model=OIDCTestResult)
async def test_provider(
    provider_id: uuid.UUID,
    _user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    community_id: uuid.UUID = Depends(_community_id),
) -> OIDCTestResult:
    """
    @brief Test discovery and a sandbox token exchange.

    The exchange posts a dummy authorization code: a 400/401 error response from
    the token endpoint proves it is reachable and client auth is evaluated.
    """
    provider = await OAuthProviderRepository(db).get_by_id(provider_id, community_id)
    if not provider:
        raise NotFoundError(message=_("OAuth provider not found"))
    if not provider.discovery_url:
        return OIDCTestResult(discovery_ok=False, error="Provider has no discovery_url")
    try:
        doc = await fetch_discovery(provider.discovery_url, settings.OIDC_HTTP_TIMEOUT)
    except (ValueError, httpx.HTTPError) as exc:
        return OIDCTestResult(discovery_ok=False, error=str(exc))

    result = OIDCTestResult(discovery_ok=True, issuer=doc.get("issuer"))
    try:
        async with httpx.AsyncClient(timeout=settings.OIDC_HTTP_TIMEOUT) as client:
            resp = await client.post(
                doc["token_endpoint"],
                data={
                    "grant_type": "authorization_code",
                    "code": "nexara-sandbox-test",
                    "redirect_uri": f"{settings.APP_BASE_URL.rstrip('/')}/api/v1/oauth/test/callback",
                    "client_id": provider.client_id,
                },
            )
        result.token_endpoint_reachable = resp.status_code in (400, 401)
        if not result.token_endpoint_reachable:
            result.error = f"Unexpected token endpoint status {resp.status_code}"
    except httpx.HTTPError as exc:
        result.error = f"Token endpoint unreachable: {exc.__class__.__name__}"
    return result
