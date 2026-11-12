"""
@file admin_storage.py
@brief Schemas for the admin storage analytics endpoints.
"""

from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel


class StorageCurrent(BaseModel):
    """@brief Latest usage: total bytes and per-category bytes."""

    total_bytes: int
    by_category: dict[str, int]


class StorageSnapshotItem(BaseModel):
    """@brief One daily snapshot point for the trend chart."""

    date: date
    total_bytes: int


class UserStorageItem(BaseModel):
    """@brief Per-user storage usage row."""

    user_id: uuid.UUID
    display_name: str
    used_bytes: int
    percent_of_total: float = 0.0


class StorageResponse(BaseModel):
    """@brief Payload for GET /admin/storage."""

    current: StorageCurrent
    snapshots: list[StorageSnapshotItem]
    per_user: list[UserStorageItem]


class UserStoragePage(BaseModel):
    """@brief Offset-paginated per-user breakdown."""

    items: list[UserStorageItem]
    total: int
    page: int
    page_size: int
