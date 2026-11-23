"""
@file deps_mail.py
@brief FastAPI dependencies for the admin email, Google mail and reply services.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import get_db, require_role

if TYPE_CHECKING:
    from app.models.user import User
    from app.services.admin_email_service import AdminEmailService
    from app.services.admin_google_mail import GoogleMailService
    from app.services.email_reply_admin_service import EmailReplyAdminService


def get_google_mail_service(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> GoogleMailService:
    """@brief Provide the Google mail connect flow (no auth: the callback is a browser redirect)."""
    from app.core.valkey import DB_CACHE, get_pool
    from app.repositories.community_repo import CommunityRepository
    from app.repositories.user_repo import UserRepository
    from app.services.admin_google_mail import GoogleMailService

    return GoogleMailService(
        CommunityRepository(db),
        UserRepository(db),
        settings,
        get_pool(settings, DB_CACHE),
    )


def get_admin_email_service(
    request: Request,
    user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AdminEmailService:
    """@brief Provide an AdminEmailService (admin only) with audit logging."""
    from app.repositories.audit_repo import AuditRepository
    from app.repositories.community_repo import CommunityRepository
    from app.services.admin_email_service import AdminEmailService

    forwarded = request.headers.get("x-forwarded-for")
    ip = forwarded.split(",")[0].strip() if forwarded else None
    if ip is None and request.client:
        ip = request.client.host
    return AdminEmailService(
        CommunityRepository(db),
        uuid.UUID(settings.COMMUNITY_ID),
        settings,
        audit_repo=AuditRepository(db),
        actor_id=user.id,
        ip_address=ip,
    )


def get_email_reply_admin_service(
    request: Request,
    user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> EmailReplyAdminService:
    """@brief Provide an EmailReplyAdminService (admin only) with audit logging."""
    from app.repositories.audit_repo import AuditRepository
    from app.repositories.community_repo import CommunityRepository
    from app.services.email_reply_admin_service import EmailReplyAdminService

    forwarded = request.headers.get("x-forwarded-for")
    ip = forwarded.split(",")[0].strip() if forwarded else None
    if ip is None and request.client:
        ip = request.client.host
    return EmailReplyAdminService(
        CommunityRepository(db),
        uuid.UUID(settings.COMMUNITY_ID),
        settings,
        audit_repo=AuditRepository(db),
        actor_id=user.id,
        ip_address=ip,
    )
