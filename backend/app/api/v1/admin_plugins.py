"""
@file admin_plugins.py
@brief Admin endpoints for plugin API keys (create, list, revoke).

All routes require admin role; every operation is written to the audit log.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.plugins import get_plugin_service
from app.core.config import Settings, get_settings
from app.core.dependencies import get_db, require_role
from app.core.exceptions import NotFoundError
from app.core.i18n import _
from app.models.plugin import PluginApiKey
from app.models.user import User
from app.plugins.api_keys import KEY_PREFIX, generate_api_key
from app.repositories.audit_repo import AuditRepository
from app.repositories.plugin_key_repo import PluginApiKeyRepository
from app.services.plugin_lifecycle import PluginLifecycleService

router = APIRouter(prefix="/admin/plugins", tags=["admin-plugins"])


class PluginApiKeyOut(BaseModel):
    """@brief Masked key metadata (never includes the secret)."""

    id: uuid.UUID
    plugin_id: str
    masked_key: str
    created_at: datetime
    last_used_at: datetime | None
    revoked_at: datetime | None


class PluginApiKeyCreated(PluginApiKeyOut):
    """@brief Creation response; ``key`` is shown exactly once."""

    key: str


def _out(k: PluginApiKey) -> dict[str, object]:
    return {
        "id": k.id,
        "plugin_id": k.plugin_id,
        "masked_key": f"{KEY_PREFIX}{k.plugin_id}_{'*' * 28}{k.key_hint}",
        "created_at": k.created_at,
        "last_used_at": k.last_used_at,
        "revoked_at": k.revoked_at,
    }


def _ip(request: Request) -> str | None:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else None


def _community(settings: Settings = Depends(get_settings)) -> uuid.UUID:
    return uuid.UUID(settings.COMMUNITY_ID)


@router.post("/{plugin_id}/api-keys", response_model=PluginApiKeyCreated, status_code=201)
async def create_api_key(
    plugin_id: str,
    request: Request,
    user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
    community_id: uuid.UUID = Depends(_community),
) -> dict[str, object]:
    """@brief Generate a key; the plaintext is returned only in this response."""
    repo = PluginApiKeyRepository(db)
    if not await repo.plugin_exists(plugin_id, community_id):
        raise NotFoundError(message=_("Plugin not found"))
    plain, hashed = generate_api_key(plugin_id)
    row = await repo.create(
        plugin_id=plugin_id, community_id=community_id, key_hash=hashed, key_hint=plain[-4:]
    )
    await AuditRepository(db).append(
        actor_id=user.id,
        action="plugin_api_key.created",
        target_type="plugin_api_key",
        target_id=row.id,
        extra_data={"plugin_id": plugin_id},
        ip_address=_ip(request),
    )
    return {**_out(row), "key": plain}


@router.get("/{plugin_id}/api-keys", response_model=list[PluginApiKeyOut])
async def list_api_keys(
    plugin_id: str,
    request: Request,
    user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
    community_id: uuid.UUID = Depends(_community),
) -> list[dict[str, object]]:
    """@brief List masked keys for a plugin."""
    repo = PluginApiKeyRepository(db)
    if not await repo.plugin_exists(plugin_id, community_id):
        raise NotFoundError(message=_("Plugin not found"))
    keys = await repo.list_for_plugin(plugin_id, community_id)
    await AuditRepository(db).append(
        actor_id=user.id,
        action="plugin_api_key.listed",
        target_type="plugin",
        extra_data={"plugin_id": plugin_id},
        ip_address=_ip(request),
    )
    return [_out(k) for k in keys]


@router.delete("/{plugin_id}/api-keys/{key_id}", response_model=PluginApiKeyOut)
async def revoke_api_key(
    plugin_id: str,
    key_id: uuid.UUID,
    request: Request,
    user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
    community_id: uuid.UUID = Depends(_community),
) -> dict[str, object]:
    """@brief Revoke a key; it stops authenticating immediately."""
    repo = PluginApiKeyRepository(db)
    key = await repo.get(key_id, plugin_id, community_id)
    if key is None:
        raise NotFoundError(message=_("API key not found"))
    key = await repo.revoke(key)
    await AuditRepository(db).append(
        actor_id=user.id,
        action="plugin_api_key.revoked",
        target_type="plugin_api_key",
        target_id=key.id,
        extra_data={"plugin_id": plugin_id},
        ip_address=_ip(request),
    )
    return _out(key)


# --- Lifecycle: two-phase install and upgrade -------------------------------


class PluginIdBody(BaseModel):
    """@brief Identifies the plugin to stage or confirm."""

    plugin_id: str


class UpgradeBody(BaseModel):
    """@brief ``confirm=false`` stages and previews; ``true`` applies the staged upgrade."""

    confirm: bool = False


def get_audit_repo(db: AsyncSession = Depends(get_db)) -> AuditRepository:
    """@brief Audit repository dependency."""
    return AuditRepository(db)


@router.post("/install-request")
async def install_request(
    body: PluginIdBody,
    request: Request,
    user: User = Depends(require_role("admin")),
    svc: PluginLifecycleService = Depends(get_plugin_service),
    audit: AuditRepository = Depends(get_audit_repo),
) -> dict[str, object]:
    """@brief Stage an install and return manifest plus permissions diff (not enabled)."""
    review = await svc.request_install(body.plugin_id)
    await audit.append(
        actor_id=user.id,
        action="plugin.install_requested",
        target_type="plugin",
        extra_data={
            "plugin_id": body.plugin_id,
            "permissions_requested": review["permissions_requested"],
        },
        ip_address=_ip(request),
    )
    return review


@router.post("/install-confirm")
async def install_confirm(
    body: PluginIdBody,
    request: Request,
    user: User = Depends(require_role("admin")),
    svc: PluginLifecycleService = Depends(get_plugin_service),
    audit: AuditRepository = Depends(get_audit_repo),
) -> dict[str, object]:
    """@brief Confirm a staged install: create, enable and issue the API key (shown once)."""
    row, key, perms = await svc.confirm_install(body.plugin_id)
    await audit.append(
        actor_id=user.id,
        action="plugin.installed",
        target_type="plugin",
        extra_data={"plugin_id": row.id, "version": row.version, "permissions_granted": perms},
        ip_address=_ip(request),
    )
    return {
        "id": row.id,
        "name": row.name,
        "version": row.version,
        "is_enabled": row.is_enabled,
        "permissions_granted": perms,
        "api_key": key,
    }


@router.put("/{plugin_id}/upgrade")
async def upgrade_plugin(
    plugin_id: str,
    body: UpgradeBody,
    request: Request,
    user: User = Depends(require_role("admin")),
    svc: PluginLifecycleService = Depends(get_plugin_service),
    audit: AuditRepository = Depends(get_audit_repo),
) -> dict[str, object]:
    """@brief Preview (stage) an upgrade, or apply it with ``confirm=true``."""
    if not body.confirm:
        review = await svc.request_upgrade(plugin_id)
        await audit.append(
            actor_id=user.id,
            action="plugin.upgrade_requested",
            target_type="plugin",
            extra_data={
                "plugin_id": plugin_id,
                "new_version": review["new_version"],
                "new_permissions": review["new_permissions"],
                "removed_permissions": review["removed_permissions"],
            },
            ip_address=_ip(request),
        )
        return review
    row, diff = await svc.confirm_upgrade(plugin_id)
    await audit.append(
        actor_id=user.id,
        action="plugin.upgraded",
        target_type="plugin",
        extra_data={
            "plugin_id": plugin_id,
            "version": row.version,
            "new_permissions": diff["new_permissions"],
            "removed_permissions": diff["removed_permissions"],
        },
        ip_address=_ip(request),
    )
    return {
        "id": row.id,
        "version": row.version,
        "permissions_granted": list(row.permissions_granted),
        **diff,
    }
