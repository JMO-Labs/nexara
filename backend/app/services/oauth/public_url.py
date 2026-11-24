"""
@file public_url.py
@brief Public origin and OAuth callback URL (what admins register at the IdP).
"""

from __future__ import annotations

from app.core.config import Settings


def public_base(settings: Settings) -> str:
    """
    @brief Public origin: APP_BASE_URL when explicitly set, else the first
           ALLOWED_ORIGINS entry, else the APP_BASE_URL default.

    The callback goes through the frontend proxy so login cookies are present.

    @param settings App settings.
    @return Origin without trailing slash.
    """
    origins = settings.allowed_origins_list
    if settings.base_url_unset and origins:
        return origins[0].rstrip("/")
    return settings.APP_BASE_URL.rstrip("/")


def callback_url(settings: Settings, slug: str) -> str:
    """
    @brief OAuth redirect URI for a provider slug.

    @param settings App settings.
    @param slug Provider slug.
    @return ``{public_base}/api/v1/oauth/{slug}/callback``.
    """
    return f"{public_base(settings)}/api/v1/oauth/{slug}/callback"
