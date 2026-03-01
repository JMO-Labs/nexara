"""
@file admin.py
@brief Admin panel API endpoints — require admin role.

Metrics, user management (list, role change, suspend, restore),
settings, and audit log. All routes require admin role.
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import get_db, require_role
from app.core.i18n import _
from app.models.user import User
from app.repositories.audit_repo import AuditRepository
from app.repositories.user_repo import UserRepository
from app.schemas.admin import (
    AdminSettingsResponse,
    AdminSettingsUpdate,
    AdminUserListItem,
    AuditLogEntry,
    MetricsResponse,
    UserRoleUpdate,
)
from app.schemas.common import MessageResponse, PaginatedResponse
from app.services.admin_service import AdminService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


def _community_id(settings: Settings = Depends(get_settings)) -> uuid.UUID:
    """@brief Extract the community UUID from settings."""
    return uuid.UUID(settings.COMMUNITY_ID)


def _build_service(
    db: AsyncSession = Depends(get_db),
    community_id: uuid.UUID = Depends(_community_id),
    settings: Settings = Depends(get_settings),
) -> AdminService:
    """@brief Build AdminService with injected dependencies."""
    return AdminService(
        session=db,
        user_repo=UserRepository(db),
        audit_repo=AuditRepository(db),
        community_id=community_id,
        settings=settings,
    )


def _client_ip(request: Request) -> str | None:
    """@brief Extract client IP from request headers or connection."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(
    _user: User = Depends(require_role("admin")),
    service: AdminService = Depends(_build_service),
) -> MetricsResponse:
    """@brief Return aggregated community, system, and WAF metrics."""
    return await service.get_metrics()


def _user_to_admin_item(u: User) -> AdminUserListItem:
    """@brief Convert User to AdminUserListItem with status from is_active."""
    return AdminUserListItem(
        id=u.id,
        username=u.username,
        display_name=u.display_name,
        email=u.email,
        avatar_url=u.avatar_url,
        bio=u.bio,
        title=u.title,
        location=u.location,
        website_url=u.website_url,
        role=u.role,
        created_at=u.created_at,
        last_seen_at=u.last_seen_at,
        status="suspended" if not u.is_active else "active",
    )


@router.get("/users", response_model=PaginatedResponse[AdminUserListItem])
async def list_users(
    _user: User = Depends(require_role("admin")),
    service: AdminService = Depends(_build_service),
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = Query(None),
    search: str | None = Query(None),
) -> PaginatedResponse[AdminUserListItem]:
    """@brief List community users with optional search (admin only)."""
    users, next_cursor = await service.list_users(
        search=search,
        limit=limit,
        cursor=cursor,
    )
    return PaginatedResponse(
        items=[_user_to_admin_item(u) for u in users],
        next_cursor=next_cursor,
        has_more=next_cursor is not None,
    )


@router.put("/users/{user_id}/role")
async def change_user_role(
    user_id: uuid.UUID,
    body: UserRoleUpdate,
    request: Request,
    user: User = Depends(require_role("admin")),
    service: AdminService = Depends(_build_service),
) -> dict[str, Any]:
    """@brief Change a user's role."""
    await service.change_role(user, user_id, body.role, _client_ip(request))
    return {"message": _("Role updated")}


@router.post("/users/{user_id}/suspend")
async def suspend_user(
    user_id: uuid.UUID,
    request: Request,
    user: User = Depends(require_role("admin")),
    service: AdminService = Depends(_build_service),
) -> dict[str, Any]:
    """@brief Suspend (deactivate) a user."""
    await service.suspend_user(user, user_id, _client_ip(request))
    return {"message": _("User suspended")}


@router.post("/users/{user_id}/restore")
async def restore_user(
    user_id: uuid.UUID,
    request: Request,
    user: User = Depends(require_role("admin")),
    service: AdminService = Depends(_build_service),
) -> dict[str, Any]:
    """@brief Restore a soft-deleted user."""
    await service.restore_user(user, user_id, _client_ip(request))
    return {"message": _("User restored")}


@router.delete("/users/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: uuid.UUID,
    request: Request,
    user: User = Depends(require_role("admin")),
    service: AdminService = Depends(_build_service),
) -> MessageResponse:
    """@brief Soft-delete a user (set deleted_at and is_active=False)."""
    await service.delete_user(user, user_id, _client_ip(request))
    return MessageResponse(message=_("User deleted"))


@router.get("/settings", response_model=AdminSettingsResponse)
async def get_admin_settings(
    _user: User = Depends(require_role("admin")),
    service: AdminService = Depends(_build_service),
) -> AdminSettingsResponse:
    """@brief Return admin-configurable settings."""
    return service.get_admin_settings()


@router.put("/settings", response_model=AdminSettingsResponse)
async def update_admin_settings(
    data: AdminSettingsUpdate,
    request: Request,
    user: User = Depends(require_role("admin")),
    service: AdminService = Depends(_build_service),
) -> AdminSettingsResponse:
    """@brief Update admin settings (Phase 1: audit log only)."""
    return await service.update_admin_settings(user, data, _client_ip(request))


@router.get("/audit-log", response_model=PaginatedResponse[AuditLogEntry])
async def get_audit_log(
    _user: User = Depends(require_role("admin")),
    service: AdminService = Depends(_build_service),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = Query(None),
    action_filter: str | None = Query(None),
) -> PaginatedResponse[AuditLogEntry]:
    """@brief List audit log entries enriched with actor display names."""
    from sqlalchemy import select

    entries, next_cursor = await service.list_audit_entries(
        action_filter=action_filter,
        limit=limit,
        cursor=cursor,
    )

    actor_ids = {e.actor_id for e in entries if e.actor_id is not None}
    target_user_ids = {e.target_id for e in entries if e.target_id and e.target_type == "user"}
    all_ids = actor_ids | target_user_ids

    display_map: dict[uuid.UUID, str] = {}
    if all_ids:
        result = await db.execute(select(User.id, User.display_name).where(User.id.in_(all_ids)))
        display_map = {row.id: row.display_name for row in result}

    items: list[AuditLogEntry] = []
    for e in entries:
        entry = AuditLogEntry.model_validate(e)
        if e.actor_id and e.actor_id in display_map:
            entry.actor_display_name = display_map[e.actor_id]
        if e.target_id and e.target_type == "user" and e.target_id in display_map:
            entry.target_display = display_map[e.target_id]
        items.append(entry)

    return PaginatedResponse(
        items=items,
        next_cursor=next_cursor,
        has_more=next_cursor is not None,
    )
