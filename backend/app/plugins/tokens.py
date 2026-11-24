"""
@file tokens.py
@brief Plugin bot token generation, hashing and request authentication.
"""

from __future__ import annotations

import hashlib
import secrets
from typing import TYPE_CHECKING

from app.core.exceptions import AppError, AuthenticationError
from app.core.i18n import _
from app.plugins.scopes import PLUGIN_ROUTE_SCOPES

if TYPE_CHECKING:
    from fastapi import Request
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models.user import User

TOKEN_PREFIX = "nxp_"
PLUGIN_RATE_LIMIT = "120/minute"


def hash_token(token: str) -> str:
    """@brief sha256 hex digest of a plaintext token."""
    return hashlib.sha256(token.encode()).hexdigest()


def new_token() -> tuple[str, str]:
    """@return ``(plaintext, sha256 hex)``; the plaintext is shown once, only the hash is stored."""
    plain = TOKEN_PREFIX + secrets.token_urlsafe(32)
    return plain, hash_token(plain)


def _denied() -> AppError:
    return AppError(
        code="plugin_scope_denied",
        message=_("This plugin token may not access this endpoint"),
        status_code=403,
    )


def check_scope(request: Request, granted: list[str]) -> None:
    """
    @brief Allow only allowlisted route templates whose scope was granted.
    @raises AppError 403 ``plugin_scope_denied``.
    """
    route = request.scope.get("route")
    template = getattr(route, "path", None)
    scope = PLUGIN_ROUTE_SCOPES.get((request.method.upper(), template)) if template else None
    if scope is None or scope not in granted:
        raise _denied()


def _enforce_rate(request: Request, token_id: str) -> None:
    from limits import parse

    limiter = getattr(request.app.state, "limiter", None)
    if limiter is None:
        return
    if not limiter.limiter.hit(parse(PLUGIN_RATE_LIMIT), f"plugin:{token_id}"):
        raise AppError(code="rate_limited", message=_("Too many requests"), status_code=429)


async def authenticate_plugin_token(request: Request, token: str, db: AsyncSession) -> User:
    """
    @brief Resolve an ``nxp_`` token to its bot user, enforcing scope and rate limit.

    The bot user must be active, undeleted and in the token's community.
    @raises AuthenticationError Unknown/revoked token or unusable bot.
    @raises AppError 403 ``plugin_scope_denied``; 429 when over the plugin rate limit.
    """
    from sqlalchemy import select

    from app.models.user import User
    from app.repositories.plugin_repo import PluginRepository

    bad = AuthenticationError(message=_("Invalid or revoked plugin token"))
    row = await PluginRepository(db).resolve_token(hash_token(token))
    if row is None:
        raise bad
    tok, install, pc = row
    request.state.plugin_token_id = str(tok.id)
    if pc.bot_user_id is None:
        raise bad
    check_scope(request, list(install.granted_scopes))
    user = (
        await db.execute(
            select(User).where(
                User.id == pc.bot_user_id,
                User.community_id == tok.community_id,
                User.deleted_at.is_(None),
                User.is_active.is_(True),
                User.is_bot.is_(True),
            )
        )
    ).scalar_one_or_none()
    if user is None:
        raise bad
    _enforce_rate(request, str(tok.id))
    request.state.plugin_install_id = install.id
    return user
