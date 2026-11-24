"""
@file oauth2_email.py
@brief Verified email lookup for plain-OAuth2 presets (GitHub, Discord).

These providers have no ID token; their profile ``email`` is not proof of
ownership, so only an address the provider marks verified is trusted.
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from app.services.oauth.presets import PRESETS

logger = structlog.get_logger(__name__)

OAUTH2_EMAIL_PRESETS = frozenset({"github", "discord"})
_TIMEOUT = httpx.Timeout(10.0)


async def _get_json(url: str, access_token: str) -> Any:
    """@brief Authenticated GET; None on any transport/HTTP error."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                },
            )
            resp.raise_for_status()
            return resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("oauth2_email_fetch_failed", url=url, error=type(exc).__name__)
        return None


async def fetch_verified_email(preset: str | None, access_token: str) -> str | None:
    """
    @brief Return the provider-verified email for an OAuth2 preset.

    github: first entry of /user/emails that is primary and verified.
    discord: /users/@me ``email`` when ``verified`` is true.

    @param preset Provider preset key.
    @param access_token OAuth access token.
    @return Verified email, or None (unknown preset, unverified, or error).
    """
    if preset not in OAUTH2_EMAIL_PRESETS:
        return None
    p = PRESETS[preset]
    if preset == "github":
        data = await _get_json(p.emails_endpoint or "", access_token)
        for entry in data if isinstance(data, list) else []:
            if (
                isinstance(entry, dict)
                and entry.get("primary") is True
                and entry.get("verified") is True
                and entry.get("email")
            ):
                return str(entry["email"])
        return None
    data = await _get_json(p.userinfo_endpoint or "", access_token)
    if isinstance(data, dict) and data.get("verified") is True and data.get("email"):
        return str(data["email"])
    return None
