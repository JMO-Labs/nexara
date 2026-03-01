"""
@file invites.py
@brief Admin invite management endpoints: create, list, and revoke invites.

All endpoints require the ``admin`` role.  Invite tokens are generated
server-side, hashed with SHA-256, and stored in the database.  The raw
token is returned once in the create response (for email delivery).
"""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import get_db, require_role
from app.core.exceptions import ConflictError, NotFoundError
from app.core.i18n import _
from app.core.security import hash_token
from app.models.user import User
from app.repositories.audit_repo import AuditRepository
from app.repositories.invite_repo import InviteRepository
from app.schemas.auth import InviteCreateRequest, InviteResponse
from app.schemas.common import MessageResponse

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/admin/invites", tags=["admin-invites"])


def _client_ip(request: Request) -> str | None:
    """@brief Extract client IP from request headers or connection."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


class InviteCreateResponse(InviteResponse):
    """
    @brief Extends InviteResponse with the raw token (returned only at creation time).

    The raw token is included so the admin can send it to the invitee.
    It is never stored in the database and cannot be retrieved again.
    """

    raw_token: str


@router.post("", response_model=InviteCreateResponse, status_code=201)
async def create_invite(
    body: InviteCreateRequest,
    request: Request,
    admin: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Any:
    """@brief Create a new invite and return the raw token for email delivery."""
    from sqlalchemy.exc import IntegrityError

    repo = InviteRepository(db)
    audit_repo = AuditRepository(db)
    raw_token = secrets.token_urlsafe(32)
    community_id = admin.community_id
    if community_id is None:
        raise ConflictError(message=_("User must belong to a community"))

    try:
        invite = await repo.create(
            community_id=community_id,
            email=body.email,
            role=body.role,
            token_hash=hash_token(raw_token),
            created_by=admin.id,
            expires_at=datetime.now(UTC) + timedelta(days=settings.INVITE_EXPIRE_DAYS),
        )
    except IntegrityError as exc:
        logger.warning("invite_create_integrity_error", error=str(exc))
        raise ConflictError(message=_("Invite could not be created. Please try again.")) from exc

    await audit_repo.append(
        actor_id=admin.id,
        action="invite.created",
        target_type="invite",
        target_id=invite.id,
        extra_data={"email": body.email, "role": body.role},
        ip_address=_client_ip(request),
    )

    logger.info(
        "invite_created",
        invite_id=str(invite.id),
        email=body.email,
        role=body.role,
        created_by=str(admin.id),
    )

    invite_data = InviteResponse.model_validate(invite).model_dump()
    invite_data["raw_token"] = raw_token
    return InviteCreateResponse(**invite_data)


@router.get("", response_model=list[InviteResponse])
async def list_invites(
    admin: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """@brief List all invites for the admin's community (active, used, expired)."""
    repo = InviteRepository(db)
    return await repo.list_all(admin.community_id)


@router.delete("/{invite_id}", response_model=MessageResponse)
async def revoke_invite(
    invite_id: uuid.UUID,
    request: Request,
    admin: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """@brief Revoke (hard-delete) an invite before it is used."""
    repo = InviteRepository(db)
    audit_repo = AuditRepository(db)
    deleted = await repo.delete_invite(invite_id, community_id=admin.community_id)
    if not deleted:
        raise NotFoundError(message=_("Invite not found"))

    await audit_repo.append(
        actor_id=admin.id,
        action="invite.revoked",
        target_type="invite",
        target_id=invite_id,
        extra_data=None,
        ip_address=_client_ip(request),
    )

    logger.info("invite_revoked", invite_id=str(invite_id), revoked_by=str(admin.id))
    return MessageResponse(message=_("Invite revoked"))
