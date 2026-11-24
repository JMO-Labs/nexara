"""
@file sso_exchange.py
@brief Resolve a consumed SSO exchange payload to its (usable) user.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.core.exceptions import AuthenticationError
from app.core.i18n import _
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.services.auth.memorial_guard import reject_memorialized


async def resolve_exchange(
    users: UserRepository, data: dict[str, Any]
) -> tuple[User, dict[str, Any] | None]:
    """
    @brief User and held first-link for an exchange payload.

    @param users User repository (request session).
    @param data Payload stored by the callback (user_id, pending_link).
    @return (active user, pending_link dict or None).
    @raises AuthenticationError Malformed payload, unknown or deactivated user.
    """
    try:
        user_id = uuid.UUID(str(data.get("user_id")))
    except ValueError as exc:
        raise AuthenticationError(message=_("Invalid or expired code")) from exc
    user = await users.get_by_id(user_id)
    reject_memorialized(user)
    if not user or not user.is_active:
        raise AuthenticationError(message=_("User not found or deactivated"))
    pending_link = data.get("pending_link")
    return user, pending_link if isinstance(pending_link, dict) else None
