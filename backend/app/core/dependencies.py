"""
@file dependencies.py
@brief FastAPI ``Depends()`` factories for cross-cutting concerns.

Provides injectable dependencies for database sessions, the current
authenticated user, and role-based authorization guards.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Callable
from typing import TYPE_CHECKING
from uuid import UUID

import structlog
from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.i18n import _
from app.core.security import decode_token
from app.db.session import async_session_factory

if TYPE_CHECKING:
    from app.models.user import User

logger = structlog.get_logger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)
"""@brief OAuth2 bearer token extractor (does not raise on missing token)."""


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    @brief Yield an async database session.

    The session is committed on success and rolled back on exception.
    Identical to ``db.session.get_session`` but kept here so that route
    handlers only import from ``dependencies``.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_current_user(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    """
    @brief Validate the JWT bearer token and return the authenticated User.

    @param request The incoming request (for structured logging).
    @param token Bearer token extracted from the ``Authorization`` header.
    @param db Async database session.
    @param settings Application settings.
    @return The authenticated :class:`User` ORM instance.
    @raises AuthenticationError If the token is missing, invalid, or the user is not found.
    """
    from app.models.user import User

    if token is None:
        raise AuthenticationError(message=_("Authentication required"))

    try:
        payload = decode_token(token, expected_type="access", settings=settings)
    except ValueError as exc:
        raise AuthenticationError(message=str(exc)) from exc

    user_id = payload.get("sub")
    if not user_id:
        raise AuthenticationError(message=_("Invalid token payload"))

    try:
        uid = UUID(user_id)
    except (ValueError, TypeError) as exc:
        raise AuthenticationError(message=_("Invalid user identifier")) from exc

    result = await db.execute(
        select(User).where(User.id == uid, User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise AuthenticationError(message=_("User not found or deactivated"))

    return user


def require_role(*roles: str) -> Callable:
    """
    @brief Factory that returns a dependency enforcing role membership.

    Usage in a route::

        @router.delete("/users/{id}")
        async def delete_user(
            user: User = Depends(require_role("admin")),
        ): ...

    @param roles One or more role strings the user must possess.
    @return A FastAPI dependency callable.
    """

    async def _checker(
        current_user: User = Depends(get_current_user),
    ) -> User:
        """@brief Verify the current user has one of the required roles."""

        if current_user.role not in roles:
            raise AuthorizationError(
                message=_("This action requires one of the following roles: %(roles)s")
                % {"roles": ", ".join(roles)},
            )
        return current_user

    return _checker


async def get_optional_user(
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User | None:
    """
    @brief Return the authenticated user if a valid token is present, else None.

    Useful for endpoints that behave differently for logged-in vs anonymous users.
    """
    if token is None:
        return None

    from app.models.user import User

    try:
        payload = decode_token(token, expected_type="access", settings=settings)
        user_id = UUID(payload["sub"])
    except (ValueError, KeyError, TypeError):
        return None

    result = await db.execute(
        select(User).where(User.id == user_id, User.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()
