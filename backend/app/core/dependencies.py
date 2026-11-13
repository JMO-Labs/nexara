"""
@file dependencies.py
@brief FastAPI ``Depends()`` factories for cross-cutting concerns.

Provides injectable dependencies for database sessions, the current
authenticated user, and role-based authorization guards.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator, Callable
from typing import TYPE_CHECKING, Any
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
    from app.repositories.activity_repo import ActivityRepository
    from app.repositories.webhook_repo import WebhookRepository
    from app.services.ai.suggestion_service import SuggestionService
    from app.services.notifications.dispatcher import Dispatcher
    from app.services.webhook_service import WebhookService

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
        select(User).where(
            User.id == uid,
            User.deleted_at.is_(None),
            User.is_active.is_(True),
        )
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise AuthenticationError(message=_("User not found or deactivated"))

    return user


def require_role(*roles: str) -> Callable[..., Any]:
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


async def get_current_user_sse(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    """
    @brief SSE-compatible auth that falls back to a ``token`` query parameter.

    ``EventSource`` cannot set custom headers, so the frontend passes
    the JWT as ``?token=<jwt>``.  This dependency checks the
    ``Authorization`` header first, then the query string.

    @param request The incoming request.
    @param token Bearer token from the ``Authorization`` header (may be None).
    @param db Async database session.
    @param settings Application settings.
    @return The authenticated :class:`User` ORM instance.
    @raises AuthenticationError If no valid token is found.
    """
    resolved_token = token or request.query_params.get("token")
    if resolved_token is None:
        raise AuthenticationError(message=_("Authentication required"))

    from app.models.user import User

    try:
        payload = decode_token(resolved_token, expected_type="access", settings=settings)
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
        select(User).where(
            User.id == uid,
            User.deleted_at.is_(None),
            User.is_active.is_(True),
        )
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise AuthenticationError(message=_("User not found or deactivated"))
    return user


async def get_optional_user(
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User | None:
    """
    @brief Return the authenticated user if a valid token is present, else None.

    Useful for endpoints that behave differently for logged-in vs anonymous users.

    @param token Bearer token extracted from the ``Authorization`` header.
    @param db Async database session.
    @param settings Application settings.
    @return The authenticated :class:`User` instance, or None if unauthenticated.
    """
    if token is None:
        return None

    from app.models.user import User

    try:
        payload = decode_token(token, expected_type="access", settings=settings)
        user_id = UUID(payload["sub"])
    except (ValueError, KeyError, TypeError):
        return None

    result = await db.execute(select(User).where(User.id == user_id, User.deleted_at.is_(None)))
    return result.scalar_one_or_none()


async def get_activity_repo(
    db: AsyncSession = Depends(get_db),
) -> ActivityRepository:
    """
    @brief Provide an ActivityRepository instance.

    @param db Async database session.
    @return ActivityRepository instance for recording activity events.
    """
    from app.repositories.activity_repo import ActivityRepository

    return ActivityRepository(db)


async def get_webhook_repo(
    db: AsyncSession = Depends(get_db),
) -> WebhookRepository:
    """
    @brief Provide a WebhookRepository instance.

    @param db Async database session.
    @return WebhookRepository (WebhookChannel registration lives in #79).
    """
    from app.repositories.webhook_repo import WebhookRepository

    return WebhookRepository(db)


async def get_webhook_service(
    repo: WebhookRepository = Depends(get_webhook_repo),
    settings: Settings = Depends(get_settings),
) -> WebhookService:
    """
    @brief Provide a WebhookService scoped to the configured community.

    @param repo Webhook repository.
    @param settings Application settings.
    @return WebhookService instance.
    """
    from app.services.webhook_service import WebhookService

    return WebhookService(repo, uuid.UUID(settings.COMMUNITY_ID))


async def get_suggestion_service(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> SuggestionService:
    """
    @brief Provide a SuggestionService wired to its repository and the AI provider.

    @param db Async database session.
    @param settings Application settings (AI provider selection).
    @return SuggestionService instance.
    """
    from app.repositories.suggestion_repo import SuggestionRepository
    from app.services.ai.provider import get_ai_provider
    from app.services.ai.suggestion_service import SuggestionService

    return SuggestionService(SuggestionRepository(db), get_ai_provider(settings))


async def get_plugin_from_api_key(
    request: Request,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> str:
    """
    @brief Authenticate a plugin by API key (``X-Plugin-Api-Key`` or ``Bearer nxr_plugin_...``).

    Optional alternative to JWT for plugin routes; never grants user access.
    @return The authenticated plugin_id.
    @throws AuthenticationError (401) if missing, invalid or revoked.
    """
    from app.plugins.api_keys import resolve_plugin_from_key

    key = request.headers.get("x-plugin-api-key")
    if not key:
        auth = request.headers.get("authorization", "")
        key = auth[7:] if auth.lower().startswith("bearer ") else ""
    if not key:
        raise AuthenticationError(message=_("Authentication required"))
    return await resolve_plugin_from_key(db, key, uuid.UUID(settings.COMMUNITY_ID))


_dispatcher: Dispatcher | None = None


def get_dispatcher() -> Dispatcher:
    """
    @brief Return the process-wide notification Dispatcher (lazy singleton).

    @return Dispatcher bound to the shared EventBus.
    """
    global _dispatcher
    if _dispatcher is None:
        from app.services.notifications.dispatcher import Dispatcher
        from app.services.realtime.event_bus import event_bus

        _dispatcher = Dispatcher(event_bus)
    return _dispatcher
