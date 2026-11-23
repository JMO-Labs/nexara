"""
@file admin_email.py
@brief Admin: outgoing email (SMTP) settings. The password is write-only.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.core.dependencies import get_admin_email_service, require_role
from app.schemas.admin_email import (
    EmailSettingsOut,
    EmailSettingsUpdate,
    EmailTestIn,
    EmailTestOut,
)
from app.services.admin_email_service import AdminEmailService

router = APIRouter(
    prefix="/admin/email",
    tags=["admin-email"],
    dependencies=[Depends(require_role("admin"))],
)


@router.get("", response_model=EmailSettingsOut)
async def get_email_settings(
    svc: AdminEmailService = Depends(get_admin_email_service),
) -> dict[str, Any]:
    """@brief Saved settings (never the password)."""
    return await svc.get()


@router.put("", response_model=EmailSettingsOut)
async def put_email_settings(
    body: EmailSettingsUpdate, svc: AdminEmailService = Depends(get_admin_email_service)
) -> dict[str, Any]:
    """@brief Save settings; the password is encrypted at rest."""
    return await svc.update(body.model_dump(exclude_unset=True))


@router.post("/test", response_model=EmailTestOut)
async def test_email_settings(
    body: EmailTestIn, svc: AdminEmailService = Depends(get_admin_email_service)
) -> dict[str, Any]:
    """@brief Send a test message to ``to``."""
    return await svc.test(body.to)
