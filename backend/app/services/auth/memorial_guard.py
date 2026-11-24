"""
@file memorial_guard.py
@brief Refuse sign-in for memorialized accounts (401 ACCOUNT_MEMORIALIZED).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from app.core.exceptions import AppError, AuthenticationError
from app.core.i18n import _


def reject_memorialized(user: Any) -> None:
    """
    @param user A User row (or None, which is ignored).
    @throws AppError ACCOUNT_MEMORIALIZED (401) when ``memorialized_at`` is set.
    """
    if user is not None and getattr(user, "memorialized_at", None) is not None:
        raise AppError(
            code="ACCOUNT_MEMORIALIZED",
            message=_("This account has been memorialized"),
            status_code=401,
        )


async def assert_usable(user: Any, fail: Callable[[str], Awaitable[None]]) -> None:
    """
    @brief Refuse memorialised or deactivated accounts, logging ``fail(reason)`` first.

    @param user A User row.
    @param fail Sign-in failure logger taking the reason.
    @throws AppError ACCOUNT_MEMORIALIZED, or AuthenticationError when inactive.
    """
    try:
        reject_memorialized(user)
    except AppError:
        await fail("memorialized")
        raise
    if not user.is_active:
        await fail("inactive")
        raise AuthenticationError(message=_("Account is deactivated"))
