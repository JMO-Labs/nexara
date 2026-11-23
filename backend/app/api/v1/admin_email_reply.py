"""
@file admin_email_reply.py
@brief Admin: reply-by-email (IMAP) settings. The password is write-only.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.dependencies import get_email_reply_admin_service, require_role
from app.services.email_reply_admin_service import EmailReplyAdminService

router = APIRouter(
    prefix="/admin/email-reply",
    tags=["admin-email-reply"],
    dependencies=[Depends(require_role("admin"))],
)


class EmailReplyUpdate(BaseModel):
    """@brief Partial update; '' clears a text field, an omitted field is kept."""

    imap_host: str | None = Field(None, max_length=253, pattern=r"^$|^[A-Za-z0-9.-]+$")
    imap_port: int | None = Field(None, ge=1, le=65535)
    imap_user: str | None = Field(None, max_length=254)
    imap_password: str | None = Field(None, max_length=500)
    reply_address: str | None = Field(
        None, max_length=254, pattern=r"^$|^[^@\s+]+@[^@\s]+\.[^@\s]+$"
    )


@router.get("")
async def get_settings_(
    svc: EmailReplyAdminService = Depends(get_email_reply_admin_service),
) -> dict[str, Any]:
    """@brief Saved settings (never the password)."""
    return await svc.get()


@router.put("")
async def put_settings(
    body: EmailReplyUpdate, svc: EmailReplyAdminService = Depends(get_email_reply_admin_service)
) -> dict[str, Any]:
    """@brief Save settings; the password is encrypted at rest."""
    return await svc.update(body.model_dump(exclude_unset=True))


@router.post("/test")
async def test_settings(
    svc: EmailReplyAdminService = Depends(get_email_reply_admin_service),
) -> dict[str, Any]:
    """@brief Log in to the mailbox and select the inbox."""
    return await svc.test()
