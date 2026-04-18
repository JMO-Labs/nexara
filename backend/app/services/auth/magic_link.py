"""
@file magic_link.py
@brief Magic link (passwordless login) business logic.

Creates and verifies one-time magic link tokens, sends email, and returns
the authenticated user for token issuance. Orchestrated by :mod:`app.services.auth_service`.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import AuthenticationError
from app.core.i18n import _
from app.core.security import hash_token
from app.models.auth import MagicLinkToken
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.services.email.templates import EmailTemplateRenderer
from app.tasks.email_tasks import send_email


def _render_magic_link_email(magic_link_url: str) -> str:
    """@brief Render magic link email HTML."""
    renderer = EmailTemplateRenderer()
    html, _ = renderer.render("magic_link.html", {"magic_link_url": magic_link_url})
    return html


async def request_magic_link(
    session: AsyncSession,
    user_repo: UserRepository,
    settings: Settings,
    email: str,
) -> None:
    """
    @brief Request a magic link for passwordless login.

    If the user exists, generates a UUID token, stores its hash, and sends
    an email. If not found, does nothing (enumeration prevention).
    Always returns None.

    @param session Async DB session.
    @param user_repo User repository for lookups.
    @param settings App settings.
    @param email User email address.
    """
    user = await user_repo.find_by_email(email)
    if not user:
        return None
    raw_token = str(uuid.uuid4())
    token_hash_value = hash_token(raw_token)
    expires_at = datetime.now(UTC) + timedelta(minutes=15)
    magic_token = MagicLinkToken(
        user_id=user.id,
        token_hash=token_hash_value,
        expires_at=expires_at,
    )
    session.add(magic_token)
    await session.flush()
    base_url = settings.APP_BASE_URL.rstrip("/")
    magic_link_url = f"{base_url}/api/v1/auth/magic-link/verify?token={raw_token}"
    html_body = _render_magic_link_email(magic_link_url)
    subject = _("Sign in to %(app)s") % {"app": settings.APP_NAME}
    send_email.delay(to=user.email, subject=subject, html_body=html_body)
    return None


async def verify_magic_link(
    session: AsyncSession,
    user_repo: UserRepository,
    settings: Settings,
    raw_token: str,
) -> User:
    """
    @brief Verify a magic link token and return the authenticated user.

    Consumes the token (marks consumed_at). Caller must issue tokens via
    AuthService._issue_tokens.

    @param session Async DB session.
    @param user_repo User repository for lookups.
    @param settings App settings.
    @param raw_token The raw token from the magic link URL.
    @return The authenticated User instance.
    @raises AuthenticationError If token is invalid, expired, or consumed.
    """
    token_hash_value = hash_token(raw_token)
    stmt = select(MagicLinkToken).where(MagicLinkToken.token_hash == token_hash_value)
    result = await session.execute(stmt)
    stored = result.scalar_one_or_none()
    if not stored:
        raise AuthenticationError(message=_("Invalid magic link"))
    if stored.expires_at < datetime.now(UTC):
        raise AuthenticationError(message=_("Magic link has expired"))
    if stored.consumed_at is not None:
        raise AuthenticationError(message=_("Magic link has already been used"))
    stored.consumed_at = datetime.now(UTC)
    await session.flush()
    user = await user_repo.get_by_id(stored.user_id)
    if not user or not user.is_active:
        raise AuthenticationError(message=_("User not found or deactivated"))
    return user
