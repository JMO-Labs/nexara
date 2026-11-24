"""
@file admin_apprise.py
@brief Admin: Apprise alert targets (never returned with their URL) and local-network opt-in.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status

from app.core.dependencies import require_role
from app.core.deps_apprise import get_admin_apprise_service
from app.schemas.apprise import (
    AdminAppriseSettings,
    AppriseMemberResponse,
    AppriseTestResponse,
    AppriseURLCreate,
)
from app.schemas.common import MessageResponse
from app.services.admin_apprise_service import AdminAppriseService

router = APIRouter(
    prefix="/admin/apprise",
    tags=["admin-apprise"],
    dependencies=[Depends(require_role("admin"))],
)


@router.get("/targets", response_model=list[AppriseMemberResponse])
async def list_targets(
    svc: AdminAppriseService = Depends(get_admin_apprise_service),
) -> list[AppriseMemberResponse]:
    """@brief List admin alert targets."""
    return [AppriseMemberResponse.from_row(r) for r in await svc.list()]


@router.post("/targets", response_model=AppriseMemberResponse, status_code=status.HTTP_201_CREATED)
async def create_target(
    body: AppriseURLCreate, svc: AdminAppriseService = Depends(get_admin_apprise_service)
) -> AppriseMemberResponse:
    """@brief Add an admin alert target (local addresses allowed)."""
    return AppriseMemberResponse.from_row(await svc.create(body.apprise_url, body.label))


@router.delete("/targets/{url_id}", response_model=MessageResponse)
async def delete_target(
    url_id: uuid.UUID, svc: AdminAppriseService = Depends(get_admin_apprise_service)
) -> MessageResponse:
    """@brief Delete an admin alert target."""
    await svc.delete(url_id)
    return MessageResponse(message="Apprise target deleted")


@router.post("/targets/{url_id}/test", response_model=AppriseTestResponse)
async def test_target(
    url_id: uuid.UUID, svc: AdminAppriseService = Depends(get_admin_apprise_service)
) -> AppriseTestResponse:
    """@brief Send a test alert to one target."""
    ok, message = await svc.test(url_id)
    return AppriseTestResponse(status="sent" if ok else "failed", message=message)


@router.get("/settings", response_model=AdminAppriseSettings)
async def get_apprise_settings(
    svc: AdminAppriseService = Depends(get_admin_apprise_service),
) -> AdminAppriseSettings:
    """@brief Whether members may target local/private hosts."""
    return AdminAppriseSettings(allow_local=await svc.allow_local())


@router.put("/settings", response_model=AdminAppriseSettings)
async def put_apprise_settings(
    body: AdminAppriseSettings, svc: AdminAppriseService = Depends(get_admin_apprise_service)
) -> AdminAppriseSettings:
    """@brief Toggle the member local-network opt-in."""
    return AdminAppriseSettings(allow_local=await svc.set_allow_local(body.allow_local))
