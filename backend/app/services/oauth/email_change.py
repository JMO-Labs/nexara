"""
@file email_change.py
@brief Mitigations when SSO profile sync changes a user's email address.

Audits the change, kills credentials that were delivered to (or could be
requested via) the old address, and tells the old address about it.
"""

from __future__ import annotations

import html
import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.audit_repo import AuditRepository
from app.repositories.branding_repo import BrandingRepository
from app.repositories.token_repo import TokenRepository
from app.tasks.email_tasks import send_email

logger = structlog.get_logger(__name__)


async def notify_email_synced(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    community_id: uuid.UUID,
    provider_id: uuid.UUID | None,
    old_email: str,
    new_email: str,
) -> None:
    """
    @brief Audit sso.email_synced, revoke reset/refresh and magic-link tokens, mail old address.

    Password-reset tokens are stored as refresh-token rows (PasswordService), so
    revoke_all_for_user invalidates them; it also ends other sessions.

    @param session Request session.
    @param user_id User whose email changed.
    @param community_id Community (for branding).
    @param provider_id Provider that drove the change.
    @param old_email Previous address (notice recipient).
    @param new_email New address.
    """
    await AuditRepository(session).append(
        actor_id=None,
        action="sso.email_synced",
        target_type="user",
        target_id=user_id,
        extra_data={
            "old_email": old_email,
            "new_email": new_email,
            "provider_id": str(provider_id) if provider_id else None,
        },
    )
    tokens = TokenRepository(session)
    await tokens.revoke_all_for_user(user_id)
    await tokens.revoke_magic_links_for_user(user_id)

    branding = await BrandingRepository(session).get(community_id)
    community = getattr(branding, "community_name", None) or "Nexara"
    text = (
        f"The email address on your {community} account was updated from your "
        "sign-in provider. If you did not expect this change, contact an admin."
    )
    try:
        send_email.delay(
            to=old_email,
            subject=f"Your {community} email was changed",
            html_body=f"<p>{html.escape(text)}</p>",
            text_body=text,
        )
    except Exception:  # broker down must not break sign-in
        logger.warning("sso_email_notice_enqueue_failed", user_id=str(user_id))
