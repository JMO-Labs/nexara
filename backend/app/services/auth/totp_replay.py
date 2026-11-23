"""
@file totp_replay.py
@brief TOTP hardening: code normalisation, single-use claim, per-token attempt cap.
"""

from __future__ import annotations

import hashlib
import re
import uuid

from redis.exceptions import RedisError

from app.core.config import Settings
from app.core.exceptions import AppError
from app.core.valkey import DB_CACHE, get_pool

MAX_FAILURES = 5
_TOKEN_TTL = 300
_CODE_RE = re.compile(r"[0-9]{6}", re.ASCII)


def _unavailable() -> AppError:
    return AppError(code="service_unavailable", message="service_unavailable", status_code=503)


def normalize_totp(code: str) -> str | None:
    """
    @brief Canonicalise a TOTP code.

    @param code Raw user input.
    @return Stripped 6 ASCII-digit string, or None if not a TOTP-shaped code.
    """
    code = code.strip()
    return code if _CODE_RE.fullmatch(code) else None


def _fail_key(token: str) -> str:
    return f"totp:fail:{hashlib.sha256(token.encode()).hexdigest()}"


async def claim_totp_code(user_id: uuid.UUID, code: str, settings: Settings) -> bool:
    """
    @brief Atomically mark a TOTP code as used.

    @return True if first use, False if already used.
    @raises AppError 503 if Valkey is unavailable.
    """
    try:
        redis = get_pool(settings, DB_CACHE)
        return bool(await redis.set(f"totp:used:{user_id}:{code}", "1", nx=True, ex=90))
    except RedisError as exc:
        raise _unavailable() from exc


async def is_token_locked(token: str, settings: Settings) -> bool:
    """@brief True once a pending token has used up its failed attempts."""
    try:
        raw = await get_pool(settings, DB_CACHE).get(_fail_key(token))
    except RedisError as exc:
        raise _unavailable() from exc
    return int(raw or 0) >= MAX_FAILURES


async def record_failure(token: str, settings: Settings) -> None:
    """@brief Count a failed code against the pending token."""
    try:
        redis = get_pool(settings, DB_CACHE)
        key = _fail_key(token)
        await redis.incr(key)
        await redis.expire(key, _TOKEN_TTL)
    except RedisError as exc:
        raise _unavailable() from exc
