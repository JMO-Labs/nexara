"""
@file passkey.py
@brief Request/response models for /auth/passkeys.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PasskeyOut(BaseModel):
    """@brief A registered passkey (public metadata only)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    transports: list[str]
    created_at: datetime
    last_used_at: datetime | None = None


class PasskeyName(BaseModel):
    """@brief New display name."""

    name: str = Field(min_length=1, max_length=100)


class RegisterVerifyBody(BaseModel):
    """@brief Browser attestation plus a display name."""

    credential: dict[str, Any]
    name: str = Field(default="Passkey", min_length=1, max_length=100)


class LoginOptionsBody(BaseModel):
    """@brief Optional email, or a 2FA ``pending_token``, to narrow allowCredentials."""

    email: str | None = None
    pending_token: str | None = None


class LoginVerifyBody(BaseModel):
    """@brief Browser assertion; ``pending_token`` completes a 2FA step."""

    credential: dict[str, Any]
    pending_token: str | None = None
