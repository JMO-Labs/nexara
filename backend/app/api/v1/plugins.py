"""
@file plugins.py
@brief Plugin registry API: list, install, lifecycle, settings, manifest.

Mutations require admin; reads require an authenticated community member.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import get_current_user, get_db, require_role
from app.models.user import User
from app.plugins.loader import DEFAULT_PLUGINS_DIR
from app.repositories.plugin_key_repo import PluginApiKeyRepository
from app.repositories.plugin_repo import PluginRepository
from app.services.plugin_service import PluginService

router = APIRouter(prefix="/plugins", tags=["plugins"])


class PluginOut(BaseModel):
    """@brief Plugin summary."""

    id: str
    name: str
    version: str
    is_enabled: bool
    description: str = ""


class PluginInstalled(PluginOut):
    """@brief Install response; ``api_key`` is shown exactly once."""

    api_key: str


class SettingsBody(BaseModel):
    """@brief Settings key-value payload."""

    settings: dict[str, Any]


def get_plugin_service(
    db: AsyncSession = Depends(get_db), settings: Settings = Depends(get_settings)
) -> PluginService:
    """@brief Build the community-scoped plugin service."""
    return PluginService(
        PluginRepository(db),
        PluginApiKeyRepository(db),
        uuid.UUID(settings.COMMUNITY_ID),
        DEFAULT_PLUGINS_DIR,
        settings.APP_VERSION,
    )


def _desc(svc: PluginService, plugin_id: str) -> str:
    try:
        return svc.read_manifest(plugin_id).description
    except Exception:
        return ""


def _out(svc: PluginService, row: Any) -> dict[str, Any]:
    return {
        "id": row.id,
        "name": row.name,
        "version": row.version,
        "is_enabled": row.is_enabled,
        "description": _desc(svc, row.id),
    }


@router.get("", response_model=list[PluginOut])
async def list_plugins(
    _user: User = Depends(get_current_user), svc: PluginService = Depends(get_plugin_service)
) -> list[dict[str, Any]]:
    """@brief List installed plugins with enablement state."""
    return [_out(svc, r) for r in await svc.list()]


@router.post("/{plugin_id}/install", response_model=PluginInstalled)
async def install_plugin(
    plugin_id: str,
    _admin: User = Depends(require_role("admin")),
    svc: PluginService = Depends(get_plugin_service),
) -> dict[str, Any]:
    """@brief Install a plugin from the plugins dir (admin)."""
    row, key = await svc.install(plugin_id)
    return {**_out(svc, row), "api_key": key}


@router.delete("/{plugin_id}", response_model=PluginOut)
async def uninstall_plugin(
    plugin_id: str,
    _admin: User = Depends(require_role("admin")),
    svc: PluginService = Depends(get_plugin_service),
) -> dict[str, Any]:
    """@brief Soft-delete a plugin and revoke its keys (admin)."""
    return _out(svc, await svc.uninstall(plugin_id))


@router.put("/{plugin_id}/enable", response_model=PluginOut)
async def enable_plugin(
    plugin_id: str,
    _admin: User = Depends(require_role("admin")),
    svc: PluginService = Depends(get_plugin_service),
) -> dict[str, Any]:
    """@brief Enable a plugin (admin)."""
    return _out(svc, await svc.set_enabled(plugin_id, True))


@router.put("/{plugin_id}/disable", response_model=PluginOut)
async def disable_plugin(
    plugin_id: str,
    _admin: User = Depends(require_role("admin")),
    svc: PluginService = Depends(get_plugin_service),
) -> dict[str, Any]:
    """@brief Disable a plugin (admin)."""
    return _out(svc, await svc.set_enabled(plugin_id, False))


@router.get("/{plugin_id}/settings", response_model=SettingsBody)
async def get_plugin_settings(
    plugin_id: str,
    _user: User = Depends(get_current_user),
    svc: PluginService = Depends(get_plugin_service),
) -> dict[str, Any]:
    """@brief Plugin config; secret values are masked."""
    return {"settings": await svc.get_settings(plugin_id)}


@router.put("/{plugin_id}/settings", response_model=SettingsBody)
async def update_plugin_settings(
    plugin_id: str,
    body: SettingsBody,
    _admin: User = Depends(require_role("admin")),
    svc: PluginService = Depends(get_plugin_service),
) -> dict[str, Any]:
    """@brief Update plugin config key-values (admin)."""
    return {"settings": await svc.update_settings(plugin_id, body.settings)}


@router.get("/{plugin_id}/manifest")
async def get_plugin_manifest(
    plugin_id: str,
    _user: User = Depends(get_current_user),
    svc: PluginService = Depends(get_plugin_service),
) -> dict[str, Any]:
    """@brief Plugin manifest for authenticated users."""
    return svc.read_manifest(plugin_id).model_dump(mode="json")
