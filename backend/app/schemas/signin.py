"""
@file signin.py
@brief Schemas for the admin sign-in log and the member session (device) list.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class SigninRow(BaseModel):
    """@brief One sign-in attempt as shown to admins."""

    id: uuid.UUID
    time: datetime
    email: str | None
    user: str | None
    method: str
    success: bool
    reason: str | None
    ip: str | None
    device: str | None


class SigninPage(BaseModel):
    """@brief Cursor-paginated sign-in rows."""

    items: list[SigninRow]
    next_cursor: str | None = None


class SessionOut(BaseModel):
    """@brief One signed-in device (refresh-token family) of the current user."""

    family_id: uuid.UUID
    device: str
    ip: str | None
    last_seen: datetime
    current: bool
