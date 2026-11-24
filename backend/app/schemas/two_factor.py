"""
@file two_factor.py
@brief Request/response models for /auth/2fa and /admin/security.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class CodeBody(BaseModel):
    """@brief A TOTP or recovery code."""

    code: str = Field(..., min_length=6, max_length=16)


class DisableBody(BaseModel):
    """@brief Proof for disabling TOTP: the password or a valid code."""

    password: str | None = Field(default=None, max_length=256)
    code: str | None = Field(default=None, min_length=6, max_length=16)


class RecoveryCodes(BaseModel):
    """@brief Freshly issued one-time recovery codes."""

    recovery_codes: list[str]


class TwoFactorStatus(BaseModel):
    """@brief Current 2FA state of the signed-in user."""

    totp: bool
    passkeys: int
    recovery_left: int
    required: bool
    grace_until: datetime | None


class SecurityPolicy(BaseModel):
    """@brief Community 2FA policy."""

    require_2fa: Literal["off", "admins", "everyone"]
