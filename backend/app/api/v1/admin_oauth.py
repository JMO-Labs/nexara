"""
@file admin_oauth.py
@brief Admin OAuth provider management endpoints.

CRUD for OAuth providers, toggle enabled state, and OIDC discovery.
All routes require admin role. Audit log entries for mutations.
"""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import get_db, require_role
from app.core.encryption import derive_fernet_key, encrypt_secret
from app.core.exceptions import NotFoundError
from app.core.i18n import _
from app.models.oauth_provider import OAuthProvider
from app.models.user import User
from app.repositories.audit_repo import AuditRepository
from app.repositories.oauth_repo import OAuthProviderRepository
from app.schemas.common import MessageResponse
from app.schemas.oauth import (
    OAuthProviderCreate,
    OAuthProviderResponse,
    OAuthProviderUpdate,
)
from app.services.oauth.discovery import discover_endpoints
from app.services.oauth.provider_manager import ProviderManager

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/admin/oauth", tags=["admin-oauth"])


def _community_id(settings: Settings = Depends(get_settings)) -> uuid.UUID:
    """@brief Extract community UUID from settings."""
    return uuid.UUID(settings.COMMUNITY_ID)


def _client_ip(request: Request) -> str | None:
    """@brief Extract client IP from request."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


@router.get("/providers", response_model=list[OAuthProviderResponse])
async def list_providers(
    _user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
    community_id: uuid.UUID = Depends(_community_id),
) -> list[OAuthProviderResponse]:
    """@brief List all OAuth providers for the community."""
    repo = OAuthProviderRepository(db)
    items, _ = await repo.list(community_id=community_id, limit=100)
    return [OAuthProviderResponse.model_validate(p) for p in items]


@router.post("/providers", response_model=OAuthProviderResponse, status_code=201)
async def create_provider(
    body: OAuthProviderCreate,
    request: Request,
    user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    community_id: uuid.UUID = Depends(_community_id),
) -> OAuthProviderResponse:
    """@brief Create a new OAuth provider."""
    fernet_key = derive_fernet_key(settings.SECRET_KEY)
    encrypted = encrypt_secret(body.client_secret, fernet_key)

    endpoints = {}
    if body.provider_type == "oidc" and body.issuer:
        endpoints = await discover_endpoints(body.issuer.strip())

    provider = OAuthProvider(
        community_id=community_id,
        slug=body.slug,
        display_name=body.display_name,
        provider_type=body.provider_type,
        client_id=body.client_id,
        client_secret_encrypted=encrypted,
        issuer=body.issuer,
        icon_url=body.icon_url,
        scopes=body.scopes or "openid profile email groups",
        authorization_endpoint=(
            body.authorization_endpoint or endpoints.get("authorization_endpoint")
        ),
        token_endpoint=body.token_endpoint or endpoints.get("token_endpoint"),
        userinfo_endpoint=(body.userinfo_endpoint or endpoints.get("userinfo_endpoint")),
        jwks_uri=body.jwks_uri or endpoints.get("jwks_uri"),
        end_session_endpoint=(body.end_session_endpoint or endpoints.get("end_session_endpoint")),
        group_mappings=body.group_mappings,
        default_role=body.default_role,
        group_claim=body.group_claim,
        avatar_claim=body.avatar_claim,
        sub_claim=body.sub_claim,
        email_claim=body.email_claim,
        name_claim=body.name_claim,
        enabled=body.enabled,
        auto_create_users=body.auto_create_users,
    )
    repo = OAuthProviderRepository(db)
    provider = await repo.create(provider)

    audit = AuditRepository(db)
    await audit.append(
        actor_id=user.id,
        action="oauth.provider.created",
        target_type="oauth_provider",
        target_id=provider.id,
        extra_data={"slug": provider.slug},
        ip_address=_client_ip(request),
    )
    logger.info("oauth_provider_created", provider_id=str(provider.id), slug=provider.slug)
    return OAuthProviderResponse.model_validate(provider)


@router.put("/providers/{provider_id}", response_model=OAuthProviderResponse)
async def update_provider(
    provider_id: uuid.UUID,
    body: OAuthProviderUpdate,
    request: Request,
    user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    community_id: uuid.UUID = Depends(_community_id),
) -> OAuthProviderResponse:
    """@brief Update an OAuth provider."""
    repo = OAuthProviderRepository(db)
    provider = await repo.get_by_id(provider_id, community_id)
    if not provider:
        raise NotFoundError(message=_("OAuth provider not found"))

    data = body.model_dump(exclude_unset=True)
    if "client_secret" in data and data["client_secret"]:
        data["client_secret_encrypted"] = encrypt_secret(
            data.pop("client_secret"), derive_fernet_key(settings.SECRET_KEY)
        )
    elif "client_secret" in data:
        data.pop("client_secret")

    provider = await repo.update(provider, data)

    audit = AuditRepository(db)
    await audit.append(
        actor_id=user.id,
        action="oauth.provider.updated",
        target_type="oauth_provider",
        target_id=provider.id,
        extra_data={"slug": provider.slug},
        ip_address=_client_ip(request),
    )
    return OAuthProviderResponse.model_validate(provider)


@router.delete("/providers/{provider_id}", response_model=MessageResponse)
async def delete_provider(
    provider_id: uuid.UUID,
    request: Request,
    user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
    community_id: uuid.UUID = Depends(_community_id),
) -> MessageResponse:
    """@brief Delete an OAuth provider."""
    repo = OAuthProviderRepository(db)
    provider = await repo.get_by_id(provider_id, community_id)
    if not provider:
        raise NotFoundError(message=_("OAuth provider not found"))

    await repo.soft_delete(provider)
    manager = ProviderManager(db)
    manager.invalidate_cache()

    audit = AuditRepository(db)
    await audit.append(
        actor_id=user.id,
        action="oauth.provider.deleted",
        target_type="oauth_provider",
        target_id=provider_id,
        extra_data={"slug": provider.slug},
        ip_address=_client_ip(request),
    )
    return MessageResponse(message=_("OAuth provider deleted"))


@router.post("/providers/{provider_id}/toggle", response_model=OAuthProviderResponse)
async def toggle_provider(
    provider_id: uuid.UUID,
    request: Request,
    user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
    community_id: uuid.UUID = Depends(_community_id),
) -> OAuthProviderResponse:
    """@brief Toggle provider enabled state."""
    repo = OAuthProviderRepository(db)
    provider = await repo.get_by_id(provider_id, community_id)
    if not provider:
        raise NotFoundError(message=_("OAuth provider not found"))

    provider = await repo.update(provider, {"enabled": not provider.enabled})

    audit = AuditRepository(db)
    await audit.append(
        actor_id=user.id,
        action="oauth.provider.toggled",
        target_type="oauth_provider",
        target_id=provider.id,
        extra_data={"slug": provider.slug, "enabled": provider.enabled},
        ip_address=_client_ip(request),
    )
    return OAuthProviderResponse.model_validate(provider)


class OAuthDiscoverRequest(BaseModel):
    """@brief Request body for OIDC discovery."""

    issuer: str = Field(..., min_length=1)


@router.post("/discover")
async def discover_issuer(
    body: OAuthDiscoverRequest,
    _user: User = Depends(require_role("admin")),
) -> dict:
    """@brief Run OIDC discovery for an issuer URL."""
    return await discover_endpoints(body.issuer.strip())
