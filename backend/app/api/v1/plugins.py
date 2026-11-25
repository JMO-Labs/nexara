"""
@file plugins.py
@brief Plugin admin (owner / community admin) and member prefs endpoints.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Body, Depends, Query, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.client_ip import client_ip
from app.core.config import Settings, get_settings
from app.core.dependencies import get_current_user, get_db, require_role
from app.core.exceptions import AuthorizationError
from app.core.i18n import _
from app.core.plugin_deps import require_instance_owner
from app.models.user import User
from app.repositories.audit_repo import AuditRepository
from app.repositories.plugin_repo import PluginRepository
from app.repositories.user_repo import UserRepository
from app.schemas.plugin import (
    PluginCommunityOut,
    PluginInstallIn,
    PluginInstallOut,
    PluginLogsOut,
    PluginSettingsIn,
    PluginUiOut,
    PluginUninstallIn,
    PluginValuesIn,
)
from app.services.plugin_service import PluginService

router = APIRouter(prefix="/plugins", tags=["plugins"])
me_router = APIRouter(prefix="/me", tags=["plugins"])


def _plugin_service(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> PluginService:
    """@brief PluginService scoped to the caller's community with audit logging."""
    return PluginService(
        PluginRepository(db),
        UserRepository(db),
        user.community_id,
        db,
        settings,
        audit_repo=AuditRepository(db),
        actor_id=user.id,
        ip_address=client_ip(request),
    )


@router.get("", response_model=list[PluginInstallOut])
async def list_plugins(
    _owner: User = Depends(require_instance_owner),
    service: PluginService = Depends(_plugin_service),
) -> list[PluginInstallOut]:
    """@brief Installed plugins (instance owner)."""
    return await service.list_installed()


@router.post("/install", response_model=PluginInstallOut, status_code=201)
async def install_plugin(
    body: PluginInstallIn,
    _owner: User = Depends(require_instance_owner),
    service: PluginService = Depends(_plugin_service),
) -> PluginInstallOut:
    """@brief Install a plugin from a manifest URL or a package (instance owner)."""
    return await service.install(body)


@router.get("/ui", response_model=list[PluginUiOut])
async def plugin_ui(
    _user: User = Depends(get_current_user),
    service: PluginService = Depends(_plugin_service),
) -> list[PluginUiOut]:
    """@brief Prefs and composer flag specs of plugins enabled in the caller's community."""
    return await service.list_enabled_ui()


@router.delete("/{plugin_id}", status_code=204)
async def uninstall_plugin(
    plugin_id: str,
    body: PluginUninstallIn | None = Body(None),
    _owner: User = Depends(require_instance_owner),
    service: PluginService = Depends(_plugin_service),
) -> Response:
    """@brief Uninstall a plugin, optionally hiding its bot's content (instance owner)."""
    await service.uninstall(plugin_id, body.delete_content if body else False)
    return Response(status_code=204)


@router.get("/{plugin_id}/logs", response_model=PluginLogsOut)
async def plugin_logs(
    plugin_id: str,
    lines: int = Query(200, ge=1, le=200),
    _owner: User = Depends(require_instance_owner),
    service: PluginService = Depends(_plugin_service),
) -> PluginLogsOut:
    """@brief Last output lines of a package plugin from the plugin host (instance owner)."""
    return PluginLogsOut(lines=await service.logs(plugin_id, lines))


@router.patch("/{plugin_id}/communities/{community_id}", response_model=PluginCommunityOut)
async def set_plugin_community(
    plugin_id: str,
    community_id: uuid.UUID,
    body: PluginSettingsIn,
    admin: User = Depends(require_role("admin")),
    service: PluginService = Depends(_plugin_service),
) -> PluginCommunityOut:
    """@brief Enable/disable and configure a plugin in the admin's own community."""
    if community_id != admin.community_id:
        raise AuthorizationError(message=_("Not your community"))
    return await service.set_community(plugin_id, community_id, body.enabled, body.settings)


@router.get("/{plugin_id}/settings")
async def get_plugin_settings(
    plugin_id: str,
    _admin: User = Depends(require_role("admin")),
    service: PluginService = Depends(_plugin_service),
) -> dict[str, Any]:
    """@brief Plugin settings for this community; secrets masked."""
    return await service.get_settings(plugin_id)


@me_router.get("/plugin-prefs/{plugin_id}")
async def get_plugin_prefs(
    plugin_id: str,
    user: User = Depends(get_current_user),
    service: PluginService = Depends(_plugin_service),
) -> dict[str, Any]:
    """@brief The caller's preferences for an enabled plugin."""
    return await service.get_user_prefs(plugin_id, user.id)


@me_router.put("/plugin-prefs/{plugin_id}")
async def put_plugin_prefs(
    plugin_id: str,
    body: PluginValuesIn,
    user: User = Depends(get_current_user),
    service: PluginService = Depends(_plugin_service),
) -> dict[str, Any]:
    """@brief Validate and save the caller's preferences for an enabled plugin."""
    return await service.set_user_prefs(plugin_id, user.id, body.values)
