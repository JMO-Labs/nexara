"""
@file admin_oauth.py
@brief Admin OAuth/SSO provider CRUD and the SSO-only toggle.

Discovery, test and preview tools live in admin_oauth_tools.py. Logic lives in
AdminOAuthService; all routes require admin role.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.deps_oauth_admin import get_admin_oauth_service
from app.core.i18n import _
from app.models.oauth_provider import OAuthProvider
from app.schemas.common import MessageResponse
from app.schemas.oauth import (
    AdminOAuthProviderResponse,
    OAuthProviderCreate,
    OAuthProviderResponse,
    OAuthProviderUpdate,
    OIDCProviderCreate,
)
from app.services.oauth.admin_oauth_service import AdminOAuthService

router = APIRouter(prefix="/admin/oauth", tags=["admin-oauth"])
settings_router = APIRouter(prefix="/admin/settings", tags=["admin-settings"])

_Svc = Depends(get_admin_oauth_service)
_Out = AdminOAuthProviderResponse


def _out(provider: OAuthProvider, svc: AdminOAuthService) -> AdminOAuthProviderResponse:
    """@brief Serialise a provider with its computed callback URL."""
    base = OAuthProviderResponse.model_validate(provider).model_dump()
    return _Out(**base, callback_url=svc.callback_url(base["slug"]))


@router.get("/providers", response_model=list[_Out])
async def list_providers(svc: AdminOAuthService = _Svc) -> list[_Out]:
    """@brief List all OAuth providers for the community."""
    return [_out(p, svc) for p in await svc.list_all()]


@router.post("/providers", response_model=_Out, status_code=201)
async def create_provider(body: OAuthProviderCreate, svc: AdminOAuthService = _Svc) -> _Out:
    """@brief Create a new OAuth provider."""
    return _out(await svc.create(body), svc)


@router.put("/providers/{provider_id}", response_model=_Out)
async def update_provider(
    provider_id: uuid.UUID, body: OAuthProviderUpdate, svc: AdminOAuthService = _Svc
) -> _Out:
    """@brief Update an OAuth provider."""
    return _out(await svc.update(provider_id, body), svc)


@router.delete("/providers/{provider_id}", response_model=MessageResponse)
async def delete_provider(provider_id: uuid.UUID, svc: AdminOAuthService = _Svc) -> MessageResponse:
    """@brief Delete an OAuth provider."""
    await svc.delete(provider_id)
    return MessageResponse(message=_("OAuth provider deleted"))


@router.post("/providers/{provider_id}/toggle", response_model=_Out)
async def toggle_provider(provider_id: uuid.UUID, svc: AdminOAuthService = _Svc) -> _Out:
    """@brief Toggle provider enabled state."""
    return _out(await svc.toggle(provider_id), svc)


@router.post("/providers/oidc", response_model=_Out, status_code=201)
async def create_oidc_provider(body: OIDCProviderCreate, svc: AdminOAuthService = _Svc) -> _Out:
    """@brief Register an OIDC provider from its discovery URL."""
    return _out(await svc.register_oidc(body), svc)


class SsoOnlyUpdate(BaseModel):
    """@brief Request body for the SSO-only toggle."""

    enabled: bool


class SsoOnlyResponse(BaseModel):
    """@brief Current SSO-only state, with a lockout warning when enabled."""

    sso_only: bool
    warning: str | None = None


@settings_router.patch("/sso-only", response_model=SsoOnlyResponse)
async def set_sso_only(body: SsoOnlyUpdate, svc: AdminOAuthService = _Svc) -> SsoOnlyResponse:
    """@brief Enable/disable SSO-only mode (requires an enabled OIDC provider to enable)."""
    warning = await svc.set_sso_only(body.enabled)
    return SsoOnlyResponse(sso_only=body.enabled, warning=warning)
