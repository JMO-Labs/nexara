"""
@file invite.py
@brief Invite token validation for registration flows.

Used by :mod:`app.services.auth_service` when invite_token is provided.
"""

from __future__ import annotations

from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.core.i18n import _
from app.core.security import hash_token
from app.models.invite import Invite
from app.repositories.invite_repo import InviteRepository


async def validate_invite(
    invite_repo: InviteRepository,
    raw_token: str,
) -> Invite:
    """
    @brief Validate an invite token and return the Invite or raise.

    @param invite_repo Invite repository.
    @param raw_token Raw invite token string.
    @return The validated Invite.
    @raises NotFoundError If token is invalid.
    @raises ConflictError If invite already used.
    @raises AppError If invite expired.
    """
    invite = await invite_repo.find_by_token_hash(hash_token(raw_token))
    if not invite:
        raise NotFoundError(message=_("Invalid invite token"))
    if invite_repo.is_used(invite):
        raise ConflictError(message=_("Invite has already been used"))
    if invite_repo.is_expired(invite):
        raise AppError(code="GONE", message=_("Invite has expired"), status_code=410)
    return invite
