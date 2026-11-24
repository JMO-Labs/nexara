"""
@file public_url.py
@brief Public origin and OAuth callback URL (what admins register at the IdP).
"""

from __future__ import annotations

from app.core.config import Settings


def public_base(settings: Settings) -> str:
    """
    @brief Public frontend origin: first ALLOWED_ORIGINS entry, else APP_BASE_URL.

    The callback goes through the frontend proxy so login cookies are present.

    @param settings App settings.
    @return Origin without trailing slash.
    """
    origins = settings.allowed_origins_list
    return (origins[0] if origins else settings.APP_BASE_URL).rstrip("/")


def callback_url(settings: Settings, slug: str) -> str:
    """
    @brief OAuth redirect URI for a provider slug.

    @param settings App settings.
    @param slug Provider slug.
    @return ``{public_base}/api/v1/oauth/{slug}/callback``.
    """
    return f"{public_base(settings)}/api/v1/oauth/{slug}/callback"
