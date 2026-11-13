"""
@file registration.py
@brief Local-user registration flow extracted from AuthService (behavior unchanged).
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

import structlog

from app.core.exceptions import AuthorizationError, ConflictError
from app.core.i18n import _
from app.core.security import hash_password
from app.models.user import User
from app.plugins.hooks import HookRegistry
from app.repositories.calendar_repo import CalendarRepository
from app.services.auth import sso_only as _sso_only
from app.services.auth.invite import validate_invite as _validate_invite_impl

if TYPE_CHECKING:
    from app.services.auth_service import AuthService

logger = structlog.get_logger("app.services.auth_service")


async def register_user(
    svc: AuthService,
    *,
    email: str,
    username: str,
    password: str,
    display_name: str,
    invite_token: str | None = None,
    community_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """
    @brief Register a new local user (see :meth:`AuthService.register`).

    @param svc Owning AuthService (provides session, repos, settings).
    @return Dict with ``access_token``, ``expires_in``, and ``raw_refresh_token``.
    @raises ConflictError If email or username already exists.
    @raises AuthorizationError If registration is disabled or invite is required but missing.
    """
    cid = community_id or uuid.UUID(svc._settings.COMMUNITY_ID)
    await _sso_only.assert_password_auth_allowed(svc._session, cid)
    if not svc._settings.ENABLE_REGISTRATION:
        raise AuthorizationError(message=_("Registration is currently disabled"))

    role = "member"

    if svc._settings.REQUIRE_INVITE:
        if not invite_token:
            raise AuthorizationError(message=_("An invite token is required to register"))
        invite = await _validate_invite_impl(svc._invite_repo, invite_token)
        role = invite.role
    elif invite_token:
        invite = await _validate_invite_impl(svc._invite_repo, invite_token)
        role = invite.role
    else:
        invite = None

    if await svc._password_svc.check_hibp(password):
        raise ConflictError(
            message=_("This password has appeared in a data breach"),
        )

    if await svc._user_repo.email_exists(email):
        raise ConflictError(message=_("Email is already registered"))
    if await svc._user_repo.username_exists(username):
        raise ConflictError(message=_("Username is already taken"))

    user = User(
        community_id=cid,
        email=email,
        username=username,
        display_name=display_name,
        password_hash=hash_password(password),
        role=role,
    )
    user = await svc._user_repo.create(user)

    await svc._settings_repo.get_or_create(user.id, user.community_id)

    # Seed personal calendar (idempotent — safe if a prior run partially completed).
    calendar_repo = CalendarRepository(svc._session)
    await calendar_repo.ensure_personal(user.community_id, user.id)

    if invite:
        await svc._invite_repo.mark_used(invite.id, user.id)
        if svc._notification_service:
            # Notify invite creator that someone registered with their invite.
            await svc._notification_service.notify(
                user_id=invite.created_by,
                type="invite_accepted",
                payload={
                    "actor_name": user.display_name,
                    "message": _("%(user)s registered using your invite")
                    % {"user": user.display_name},
                },
                actor_id=user.id,
            )

    await HookRegistry.emit(
        "on_user_joined",
        community_id=user.community_id,
        session=svc._session,
        user_id=user.id,
    )
    logger.info("user_registered", user_id=str(user.id), email=email)
    return await svc._issue_tokens(user)
