"""
@file admin_email.py
@brief Admin: outgoing email (SMTP) settings. The password is write-only.
"""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse

from app.core.dependencies import (
    get_admin_email_service,
    get_google_mail_service,
    require_role,
)
from app.core.exceptions import AppError
from app.models.user import User
from app.schemas.admin_email import (
    EmailSettingsOut,
    EmailSettingsUpdate,
    EmailTestIn,
    EmailTestOut,
)
from app.services.admin_email_service import AdminEmailService
from app.services.admin_google_mail import GoogleMailService

logger = structlog.get_logger(__name__)

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


@router.get("/google/start")
async def google_start(
    admin: User = Depends(require_role("admin")),
    svc: GoogleMailService = Depends(get_google_mail_service),
) -> dict[str, str]:
    """@brief Google consent URL for the browser to open."""
    return {"url": await svc.start(admin.id)}


#: No router-level auth: Google redirects the browser here. The state (bound to the
#: initiating admin in Valkey) is the credential and is re-checked in the service.
callback_router = APIRouter(prefix="/admin/email", tags=["admin-email"])
_DONE = "/app/admin?tab=email&google="


@callback_router.get("/google/callback")
async def google_callback(
    code: str = "",
    state: str = "",
    error: str = "",
    svc: GoogleMailService = Depends(get_google_mail_service),
) -> RedirectResponse:
    """@brief Finish the Google connection, then send the browser back to the Email tab."""
    if error or not code or not state:
        return RedirectResponse(_DONE + "error", status_code=303)
    try:
        await svc.complete(code, state)
    except AppError as exc:
        logger.warning("google_mail_connect_failed", code=exc.code)
        return RedirectResponse(_DONE + "error", status_code=303)
    return RedirectResponse(_DONE + "connected", status_code=303)
