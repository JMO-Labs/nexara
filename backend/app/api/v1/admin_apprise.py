"""
@file admin_apprise.py
@brief Admin: Apprise alert targets (never returned with their URL) and local-network opt-in.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import get_db, require_role
from app.models.user import User
from app.repositories.apprise_repo import AppriseRepository
from app.repositories.audit_repo import AuditRepository
from app.schemas.apprise import (
    AdminAppriseSettings,
    AppriseTestResponse,
    AppriseURLCreate,
    AppriseURLResponse,
)
from app.schemas.common import MessageResponse
from app.services.admin_apprise_service import AdminAppriseService

router = APIRouter(
    prefix="/admin/apprise",
    tags=["admin-apprise"],
    dependencies=[Depends(require_role("admin"))],
)


def _service(
    request: Request,
    user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AdminAppriseService:
    """@brief Admin-only service with audit logging."""
    fwd = request.headers.get("x-forwarded-for")
    ip = fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else None)
    return AdminAppriseService(
        AppriseRepository(db),
        uuid.UUID(settings.COMMUNITY_ID),
        AuditRepository(db),
        user.id,
        ip,
    )


@router.get("/targets", response_model=list[AppriseURLResponse])
async def list_targets(svc: AdminAppriseService = Depends(_service)) -> list[AppriseURLResponse]:
    """@brief List admin alert targets."""
    return [AppriseURLResponse.model_validate(r) for r in await svc.list()]


@router.post("/targets", response_model=AppriseURLResponse, status_code=status.HTTP_201_CREATED)
async def create_target(
    body: AppriseURLCreate, svc: AdminAppriseService = Depends(_service)
) -> AppriseURLResponse:
    """@brief Add an admin alert target (local addresses allowed)."""
    return AppriseURLResponse.model_validate(await svc.create(body.apprise_url, body.label))


@router.delete("/targets/{url_id}", response_model=MessageResponse)
async def delete_target(
    url_id: uuid.UUID, svc: AdminAppriseService = Depends(_service)
) -> MessageResponse:
    """@brief Delete an admin alert target."""
    await svc.delete(url_id)
    return MessageResponse(message="Apprise target deleted")


@router.post("/targets/{url_id}/test", response_model=AppriseTestResponse)
async def test_target(
    url_id: uuid.UUID, svc: AdminAppriseService = Depends(_service)
) -> AppriseTestResponse:
    """@brief Send a test alert to one target."""
    ok, message = await svc.test(url_id)
    return AppriseTestResponse(status="sent" if ok else "failed", message=message)


@router.get("/settings", response_model=AdminAppriseSettings)
async def get_apprise_settings(
    svc: AdminAppriseService = Depends(_service),
) -> AdminAppriseSettings:
    """@brief Whether members may target local/private hosts."""
    return AdminAppriseSettings(allow_local=await svc.allow_local())


@router.put("/settings", response_model=AdminAppriseSettings)
async def put_apprise_settings(
    body: AdminAppriseSettings, svc: AdminAppriseService = Depends(_service)
) -> AdminAppriseSettings:
    """@brief Toggle the member local-network opt-in."""
    return AdminAppriseSettings(allow_local=await svc.set_allow_local(body.allow_local))
