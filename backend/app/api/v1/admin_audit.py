"""
@file admin_audit.py
@brief Admin: GET /admin/audit-log (alias /admin/audit) and /admin/audit.csv.

There is deliberately no DELETE/PUT/PATCH: the log is append-only (retention aside).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.client_ip import client_ip
from app.core.dependencies import get_db, require_role
from app.db.session import async_session_factory
from app.models.user import User
from app.schemas.admin import AuditLogEntry
from app.schemas.common import PaginatedResponse
from app.services.admin_audit_service import AdminAuditService

router = APIRouter(prefix="/admin", tags=["admin-audit"])


def get_admin_audit_service(
    request: Request,
    user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> AdminAuditService:
    """@brief AdminAuditService (admin only) with a streaming reader session."""
    return AdminAuditService(db, user.id, client_ip(request), async_session_factory)


def _filters(
    q: str | None = Query(None, max_length=100),
    actor_id: uuid.UUID | None = None,
    action_prefix: str | None = Query(None, max_length=100),
    action_filter: str | None = Query(None, max_length=100),
    since: datetime | None = None,
    until: datetime | None = None,
) -> dict[str, Any]:
    """@brief Shared filter query params (``action_filter`` is the legacy name)."""
    return {
        "q": q,
        "actor_filter": actor_id,
        "action_filter": action_prefix or action_filter,
        "since": since,
        "until": until,
    }


@router.get("/audit-log", response_model=PaginatedResponse[AuditLogEntry])
@router.get("/audit", response_model=PaginatedResponse[AuditLogEntry], include_in_schema=False)
async def get_audit_log(
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = Query(None),
    filters: dict[str, Any] = Depends(_filters),
    svc: AdminAuditService = Depends(get_admin_audit_service),
) -> PaginatedResponse[AuditLogEntry]:
    """@brief Filtered audit entries, newest first, with actor display names."""
    return await svc.list_page(limit=limit, cursor=cursor, **filters)


@router.get("/audit.csv")
async def export_audit(
    filters: dict[str, Any] = Depends(_filters),
    svc: AdminAuditService = Depends(get_admin_audit_service),
) -> StreamingResponse:
    """@brief Stream the filtered log as CSV (max 50 000 rows); the export is audited."""
    body = await svc.export_csv(**filters)
    return StreamingResponse(
        body,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="audit.csv"'},
    )
