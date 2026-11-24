"""
@file admin_oauth_tools.py
@brief Admin SSO tools: presets, OIDC discovery, provider test, group-mapping preview.

All routes require admin role and never return secrets.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.core.dependencies import require_role
from app.core.deps_oauth_admin import get_admin_oauth_service
from app.models.user import User
from app.schemas.oauth import GroupMappingPreview, OIDCTestResult
from app.services.oauth.admin_oauth_service import AdminOAuthService
from app.services.oauth.discovery import DiscoveryEndpoints, discover_endpoints
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
    svc: AdminOAuthService = Depends(get_admin_oauth_service),
) -> GroupMappingPreview:
    """@brief Sandbox: resolve the provider's group mapping (optionally for sample groups)."""
    entries = await svc.preview_groups(provider_id, groups)
    return GroupMappingPreview.model_validate({"entries": entries})


@router.post("/providers/{provider_id}/test", response_model=OIDCTestResult)
async def test_provider(
    provider_id: uuid.UUID, svc: AdminOAuthService = Depends(get_admin_oauth_service)
) -> OIDCTestResult:
    """@brief Test discovery and a sandbox token exchange."""
    return await svc.test(provider_id)


class TestLoginStart(BaseModel):
    """@brief IdP authorize URL for the admin test-login popup."""

    authorize_url: str


@router.post("/providers/{provider_id}/test-login", response_model=TestLoginStart)
async def start_test_login(
    provider_id: uuid.UUID, svc: AdminOAuthService = Depends(get_admin_oauth_service)
) -> TestLoginStart:
    """@brief Start a test login: real IdP round-trip, nothing provisioned."""
    return TestLoginStart(authorize_url=await svc.start_test_login(provider_id))


@router.get("/test-login/{result_id}")
async def read_test_login(
    result_id: str, svc: AdminOAuthService = Depends(get_admin_oauth_service)
) -> dict[str, Any]:
    """@brief One-time read of the calling admin's test-login result."""
    return await svc.read_test_result(result_id)


@router.get("/callback-url")
async def callback_url_template(
    svc: AdminOAuthService = Depends(get_admin_oauth_service),
) -> dict[str, str]:
    """@brief Redirect URI template (``{slug}`` placeholder) for providers not yet saved."""
    return {"template": svc.callback_url("{slug}")}
