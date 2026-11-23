"""
@file cookies.py
@brief Shared cookie policy helpers.
"""

from __future__ import annotations

from app.core.config import Settings


def should_secure_cookie(settings: Settings) -> bool:
    """@brief Return True if cookies should use the Secure flag (origins are HTTPS)."""
    origins = settings.allowed_origins_list
    return all(o.startswith("https://") for o in origins) if origins else True
