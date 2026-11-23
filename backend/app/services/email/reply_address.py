"""
@file reply_address.py
@brief Helpers for the reply-by-email address and "is it ready" check.
"""

from __future__ import annotations

from typing import Any

from app.core.features import is_enabled


def reply_local_part(address: str | None) -> str | None:
    """@return The local part of the configured reply address (no plus tag), or None."""
    if not address or "@" not in address:
        return None
    return address.rpartition("@")[0].split("+")[0] or None


def is_configured(community: Any) -> bool:
    """@return True when every IMAP field and the reply address are set."""
    return bool(
        community.inbound_imap_host
        and community.inbound_imap_user
        and community.inbound_imap_password
        and reply_local_part(community.inbound_reply_address)
        and community.inbound_authserv_id
    )


def is_active(community: Any) -> bool:
    """@return True when the feature is on and the settings are complete."""
    return is_enabled(community, "reply_by_email") and is_configured(community)


def with_token(address: str, token: str) -> str:
    """@return ``local+<token>@domain`` for the configured address."""
    local, _, domain = address.rpartition("@")
    return f"{local.split('+')[0]}+{token}@{domain}"
