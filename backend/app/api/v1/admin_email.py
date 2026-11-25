"""
@file admin_email.py
@brief Admin: outgoing email (SMTP) settings. The password is write-only.
"""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, Cookie, Depends, Request, Response
from fastapi.responses import RedirectResponse

from app.core.client_ip import client_ip
from app.core.config import Settings, get_settings
from app.core.cookies import should_secure_cookie
from app.core.dependencies import require_role
from app.core.deps_mail import get_admin_email_service, get_google_mail_service
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
    response: Response,
    admin: User = Depends(require_role("admin")),
    svc: GoogleMailService = Depends(get_google_mail_service),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    """@brief Google consent URL; also binds the flow to this browser via a cookie."""
    url, nonce = await svc.start(admin.id)
    response.set_cookie(
        NONCE_COOKIE,
        nonce,
        max_age=600,
        httponly=True,
        secure=should_secure_cookie(settings),
        samesite="lax",
        path=NONCE_PATH,
    )
    return {"url": url}


#: No router-level auth: Google redirects the browser here. The state (bound to the
#: initiating admin in Valkey) is the credential and is re-checked in the service.
callback_router = APIRouter(prefix="/admin/email", tags=["admin-email"])
_DONE = "/app/admin?tab=email&google="
NONCE_COOKIE = "nx_gmail_nonce"
NONCE_PATH = "/api/v1/admin/email/google"


def _redirect(result: str) -> RedirectResponse:
    resp = RedirectResponse(_DONE + result, status_code=303)
    resp.delete_cookie(NONCE_COOKIE, path=NONCE_PATH)
    return resp


@callback_router.get("/google/callback")
async def google_callback(
    request: Request,
    code: str = "",
    state: str = "",
    error: str = "",
    nonce: str | None = Cookie(None, alias=NONCE_COOKIE),
    svc: GoogleMailService = Depends(get_google_mail_service),
) -> RedirectResponse:
    """@brief Finish the Google connection, then send the browser back to the Email tab."""
    if error or not code or not state:
        return _redirect("error")
    try:
        await svc.complete(code, state, nonce, client_ip(request))
    except AppError as exc:
        logger.warning("google_mail_connect_failed", code=exc.code)
        return _redirect("error")
    return _redirect("connected")
