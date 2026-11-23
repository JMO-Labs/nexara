"""
@file smtp_settings.py
@brief SmtpConfig and resolve_smtp: DB row (communities.smtp_*) wins over env SMTP_*.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.encryption import decrypt_secret, derive_fernet_key
from app.models.community import Community


@dataclass
class SmtpConfig:
    """@brief Everything needed to open an SMTP connection and build From."""

    host: str
    port: int
    security: str  # starttls | ssl | none
    user: str
    password: str
    from_addr: str
    from_name: str | None = None
    auth: str = "password"  # password | google_oauth
    google_refresh: str | None = None
    #: Set when read from the DB row; send_email records last ok/error on it.
    community_id: uuid.UUID | None = None


def infer_security(port: int) -> str:
    """@brief 465 means implicit TLS, anything else STARTTLS."""
    return "ssl" if port == 465 else "starttls"


def config_from_row(row: Community, secret_key: str) -> SmtpConfig | None:
    """@brief SmtpConfig from the community row, or None when smtp_host is unset."""
    if not row.smtp_host:
        return None
    key = derive_fernet_key(secret_key)
    port = row.smtp_port or 587
    refresh = row.smtp_google_refresh
    return SmtpConfig(
        host=row.smtp_host,
        port=port,
        security=row.smtp_security or infer_security(port),
        user=row.smtp_user or "",
        password=decrypt_secret(row.smtp_password, key) if row.smtp_password else "",
        from_addr=row.smtp_from or row.smtp_user or "noreply@nexara.local",
        from_name=row.smtp_from_name,
        auth=row.smtp_auth or "password",
        google_refresh=decrypt_secret(refresh, key) if refresh else None,
        community_id=row.id,
    )


def config_from_env(settings: Settings) -> SmtpConfig | None:
    """@brief SmtpConfig from env SMTP_*, or None when SMTP_HOST is empty."""
    if not settings.SMTP_HOST:
        return None
    return SmtpConfig(
        host=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        security=infer_security(settings.SMTP_PORT),
        user=settings.SMTP_USER,
        password=settings.SMTP_PASSWORD,
        from_addr=settings.SMTP_FROM or "noreply@nexara.local",
    )


async def resolve_smtp(session: AsyncSession, community_id: uuid.UUID) -> SmtpConfig | None:
    """
    @brief Resolve the SMTP config for a community.
    @param session Async DB session.
    @param community_id Tenant id.
    @return DB config when ``smtp_host`` is set, else env SMTP_*, else None.
    """
    settings = get_settings()
    row = await session.get(Community, community_id)
    return (config_from_row(row, settings.SECRET_KEY) if row is not None else None) or (
        config_from_env(settings)
    )
