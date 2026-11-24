"""
@file admin_oauth_tools.py
@brief Admin SSO tools: presets, OIDC discovery, provider test, group-mapping preview.

All routes require admin role and never return secrets.
"""

from __future__ import annotations

import uuid
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.admin_oauth import _community_id
from app.core.config import Settings, get_settings
from app.core.dependencies import get_db, require_role
from app.core.exceptions import NotFoundError
from app.core.i18n import _
from app.models.user import User
from app.repositories.oauth_repo import OAuthProviderRepository
from app.repositories.subgroup_repo import SubgroupRepository
from app.schemas.oauth import GroupMappingPreview, OIDCTestResult
from app.services.oauth.discovery import DiscoveryEndpoints, discover_endpoints, fetch_discovery
from app.services.oauth.group_mapper import preview_group_mapping
from app.services.oauth.presets import PRESETS

router = APIRouter(prefix="/admin/oauth", tags=["admin-oauth"])


@router.get("/presets")
async def list_presets(_user: User = Depends(require_role("admin"))) -> list[dict[str, Any]]:
    """@brief List built-in SSO provider presets."""
    return [p.to_dict(k) for k, p in PRESETS.items()]


class OAuthDiscoverRequest(BaseModel):
    """@brief Request body for OIDC discovery."""

    issuer: str = Field(..., min_length=1)


@router.post("/discover")
async def discover_issuer(
    body: OAuthDiscoverRequest,
    _user: User = Depends(require_role("admin")),
) -> DiscoveryEndpoints:
    """@brief Run OIDC discovery for an issuer URL."""
    return await discover_endpoints(body.issuer.strip())


@router.get("/providers/{provider_id}/group-mapping-preview", response_model=GroupMappingPreview)
async def group_mapping_preview(
    provider_id: uuid.UUID,
    groups: list[str] | None = Query(default=None),
    _user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
    community_id: uuid.UUID = Depends(_community_id),
) -> GroupMappingPreview:
    """@brief Sandbox: resolve the provider's group mapping (optionally for sample groups)."""
    provider = await OAuthProviderRepository(db).get_by_id(provider_id, community_id)
    if not provider:
        raise NotFoundError(message=_("OAuth provider not found"))
    entries = await preview_group_mapping(
        SubgroupRepository(db), community_id, provider.claim_mapping, groups
    )
    return GroupMappingPreview.model_validate({"entries": entries})


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
        callback_url = f"{settings.APP_BASE_URL.rstrip('/')}/api/v1/oauth/test/callback"
        async with httpx.AsyncClient(timeout=settings.OIDC_HTTP_TIMEOUT) as client:
            resp = await client.post(
                doc["token_endpoint"],
                data={
                    "grant_type": "authorization_code",
                    "code": "nexara-sandbox-test",
                    "redirect_uri": callback_url,
                    "client_id": provider.client_id,
                },
            )
        result.token_endpoint_reachable = resp.status_code in (400, 401)
        if not result.token_endpoint_reachable:
            result.error = f"Unexpected token endpoint status {resp.status_code}"
    except httpx.HTTPError as exc:
        result.error = f"Token endpoint unreachable: {exc.__class__.__name__}"
    return result
