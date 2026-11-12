"""@file api_keys.py
@brief Plugin API key generation, parsing and verification.

Format: ``nxr_plugin_{plugin_id}_{32 hex}``. Only a bcrypt hash is stored.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime

import bcrypt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError
from app.core.i18n import _
from app.repositories.plugin_key_repo import PluginApiKeyRepository

KEY_PREFIX = "nxr_plugin_"
_HEX = frozenset("0123456789abcdef")


def generate_api_key(plugin_id: str) -> tuple[str, str]:
    """@brief Create a key. @return (plaintext, bcrypt hash)."""
    plain = f"{KEY_PREFIX}{plugin_id}_{secrets.token_hex(16)}"
    return plain, bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_api_key(plain: str, hashed: str) -> bool:
    """@brief Check a plaintext key against its bcrypt hash."""
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except ValueError:
        return False


def parse_api_key(key: str) -> str | None:
    """@brief Extract plugin_id from a key, or None if malformed."""
    if not key.startswith(KEY_PREFIX):
        return None
    plugin_id, _sep, secret = key[len(KEY_PREFIX) :].rpartition("_")
    if not plugin_id or len(secret) != 32 or not set(secret) <= _HEX:
        return None
    return plugin_id


async def resolve_plugin_from_key(
    session: AsyncSession, key: str, community_id: uuid.UUID
) -> str:
    """
    @brief Validate a plugin API key against stored hashes.
    @return The plugin_id the key belongs to.
    @throws AuthenticationError if malformed, unknown, revoked, or the plugin is disabled/removed.
    """
    invalid = AuthenticationError(message=_("Invalid plugin API key"))
    plugin_id = parse_api_key(key)
    if plugin_id is None:
        raise invalid
    rows = await PluginApiKeyRepository(session).active_keys_for_plugin(plugin_id, community_id)
    for row in rows:
        if row.revoked_at is None and verify_api_key(key, row.key_hash):
            row.last_used_at = datetime.now(UTC)
            return plugin_id
    raise invalid
