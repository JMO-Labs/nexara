"""
@file totp_replay.py
@brief Single-use enforcement for TOTP codes (Valkey, 90 s TTL).
"""

from __future__ import annotations

import uuid

from app.core.config import Settings
from app.core.valkey import DB_CACHE, get_pool


async def claim_totp_code(user_id: uuid.UUID, code: str, settings: Settings) -> bool:
    """
    @brief Atomically mark a TOTP code as used.

    @param user_id User UUID.
    @param code The TOTP code just verified.
    @param settings Application settings.
    @return True if first use, False if the code was already used.
    """
    redis = get_pool(settings, DB_CACHE)
    return bool(await redis.set(f"totp:used:{user_id}:{code}", "1", nx=True, ex=90))
