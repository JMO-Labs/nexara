"""
@file admin_email.py
@brief Schemas for /admin/email (SMTP settings). The password is write-only.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

_HOST = r"^$|^[A-Za-z0-9.-]+$"
_ADDR = r"^$|^[^@\s]+@[^@\s]+\.[^@\s]+$"


class EmailSettingsUpdate(BaseModel):
    """@brief Partial update; '' clears a text field, an omitted field is kept."""

    host: str | None = Field(None, max_length=253, pattern=_HOST)
    # Fixed set keeps the Test button from probing arbitrary ports.
    port: Literal[25, 465, 587, 1025, 2525] | None = None
    security: Literal["starttls", "ssl", "none"] | None = None
    user: str | None = Field(None, max_length=254)
    password: str | None = Field(None, max_length=500)
    from_addr: str | None = Field(None, max_length=254, pattern=_ADDR)
    from_name: str | None = Field(None, max_length=100)
    auth: Literal["password", "google_oauth"] | None = None


class EmailSettingsOut(BaseModel):
    """@brief Saved settings; never the password or refresh token."""

    host: str
    port: int
    security: str
    user: str
    from_addr: str
    from_name: str
    auth: str
    has_password: bool
    has_google_refresh: bool
    configured: bool
    last_ok_at: datetime | None
    last_error: str | None


class EmailTestIn(BaseModel):
    """@brief Recipient for the test message."""

    to: str = Field(max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class EmailTestOut(BaseModel):
    """@brief Test-send outcome."""

    ok: bool
    error: str | None = None
    #: auth_failed|connect_failed|tls_failed|rejected|timeout|unknown
    category: str | None = None
