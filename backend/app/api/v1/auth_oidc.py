"""
@file auth_oidc.py
@brief Deprecated OIDC redirects and JWKS endpoint (included in the auth router).
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Cookie, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import get_db
from app.core.i18n import _
from app.core.security import get_jwks

router = APIRouter(tags=["auth"])


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
