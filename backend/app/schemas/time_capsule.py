"""
@file time_capsule.py
@brief Pydantic schemas for time capsules. ``CapsuleSealed`` carries no
       body/media fields at all so they cannot leak before opening.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class CapsuleRecipient(BaseModel):
    """@brief One audience entry; ``target_id`` is omitted for ``community``."""

    kind: Literal["user", "subgroup", "community", "household"]
    target_id: uuid.UUID | None = None


class CapsuleCreate(BaseModel):
    """@brief Request body for sealing a capsule."""

    title: str = Field(min_length=1, max_length=120)
    body: str = Field(default="", max_length=20000)
    media_ids: list[uuid.UUID] = Field(default_factory=list, max_length=10)
    open_at: datetime
    recipients: list[CapsuleRecipient] = Field(min_length=1, max_length=50)


class CapsuleAuthor(BaseModel):
    """@brief Minimal author profile."""

    id: uuid.UUID
    display_name: str


class CapsuleSealed(BaseModel):
    """@brief What a recipient sees before the capsule opens."""

    id: uuid.UUID
    title: str
    author: CapsuleAuthor
    open_at: datetime
    recipients_summary: str


class CapsuleOpen(CapsuleSealed):
    """@brief Full capsule (opened, or viewer is the author)."""

    body: str
    media: list[uuid.UUID]
    opened_at: datetime | None = None


class CapsuleList(BaseModel):
    """@brief Capsules grouped for the page tabs."""

    sealed: list[CapsuleSealed]
    opened: list[CapsuleOpen]
    mine: list[CapsuleOpen]
