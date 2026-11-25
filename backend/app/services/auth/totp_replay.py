"""
@file totp_replay.py
@brief TOTP hardening: code normalisation, single-use claim, per-token attempt cap.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from redis.exceptions import RedisError
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import AppError, AuthenticationError
from app.core.i18n import _
from app.core.security import hash_token
from app.core.valkey import DB_CACHE, get_pool
from app.models.auth import UserBackupCode
from app.models.user import User

MAX_FAILURES = 5
MAX_USER_FAILURES = 10
_USER_TTL = 900
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


def _user_key(user_id: uuid.UUID) -> str:
    return f"totp:fail:user:{user_id}"


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


async def reserve_attempt(token: str, user_id: uuid.UUID, settings: Settings) -> bool:
    """
    @brief Atomically count one 2FA attempt against the token and the account.

    Both counters are INCR + EXPIRE NX in one MULTI so the TTL always exists.

    @return False when either cap (5 per token, 10 per user/15 min) is exceeded.
    @raises AppError 503 if Valkey is unavailable.
    """
    tkey, ukey = _fail_key(token), _user_key(user_id)
    try:
        async with get_pool(settings, DB_CACHE).pipeline(transaction=True) as pipe:
            pipe.incr(tkey)
            pipe.expire(tkey, _TOKEN_TTL, nx=True)
            pipe.incr(ukey)
            pipe.expire(ukey, _USER_TTL, nx=True)
            res = await pipe.execute()
    except RedisError as exc:
        raise _unavailable() from exc
    return int(res[0]) <= MAX_FAILURES and int(res[2]) <= MAX_USER_FAILURES


async def finish_pending(
    token: str,
    payload: dict[str, Any],
    user: User,
    settings: Settings,
    fail: Callable[..., Awaitable[None]],
    method: str,
) -> None:
    """
    @brief Spend a verified ``2fa_pending`` token (single-use) and reset attempt counters.

    The token is denylisted in Valkey until its ``exp``.

    Uses DB_CACHE like ``totp:used``; both assume the cache DB is not under an
    ``allkeys-*`` eviction policy (an evicted key would reopen the replay window).

    @param fail ``log_failure`` partial; a replay is logged as ``bad_2fa_session``.
    @param method Sign-in method recorded on that failure row.
    @raises AuthenticationError If the token was already spent.
    @raises AppError 503 if Valkey is unavailable.
    """
    ttl = max(1, int(payload["exp"] - datetime.now(UTC).timestamp()) + 1)
    key = f"totp:spent:{hashlib.sha256(token.encode()).hexdigest()}"
    try:
        fresh = await get_pool(settings, DB_CACHE).set(key, "1", nx=True, ex=ttl)
    except RedisError as exc:
        raise _unavailable() from exc
    if not fresh:
        await fail(user, user.email, method, "bad_2fa_session")
        raise AuthenticationError(message=_("Invalid 2FA session"))
    await clear_user_attempts(user.id, settings)


async def clear_user_attempts(user_id: uuid.UUID, settings: Settings) -> None:
    """@brief Reset the per-account counter after a successful 2FA login."""
    try:
        await get_pool(settings, DB_CACHE).delete(_user_key(user_id))
    except RedisError as exc:
        raise _unavailable() from exc


async def consume_backup_code(session: AsyncSession, user_id: uuid.UUID, code: str) -> bool:
    """
    @brief Spend an unused backup code with one atomic UPDATE ... RETURNING.

    Input is normalised (trimmed, upper-cased, spaces/dashes dropped) so codes
    typed in lowercase or grouped still match.

    @return True only if this call flipped the row (concurrent callers lose).
    """
    code = code.strip().upper().replace(" ", "").replace("-", "")
    stmt = (
        update(UserBackupCode)
        .where(
            UserBackupCode.user_id == user_id,
            UserBackupCode.code_hash == hash_token(code),
            UserBackupCode.used_at.is_(None),
        )
        .values(used_at=datetime.now(UTC))
        .returning(UserBackupCode.id)
        .execution_options(synchronize_session=False)
    )
    return (await session.execute(stmt)).first() is not None
