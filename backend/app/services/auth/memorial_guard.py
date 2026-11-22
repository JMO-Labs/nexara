"""
@file memorial_guard.py
@brief Refuse sign-in for memorialized accounts (401 ACCOUNT_MEMORIALIZED).
"""

from __future__ import annotations

from typing import Any

from app.core.exceptions import AppError
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
