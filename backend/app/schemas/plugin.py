"""
@file plugin.py
@brief Strict Pydantic read schemas for Plugin and PluginData.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PluginRead(BaseModel):
    """@brief Strictly typed view of a Plugin row."""

    model_config = ConfigDict(strict=True, from_attributes=True)

    id: str
    community_id: UUID
    name: str
    version: str
    is_enabled: bool
    permissions_granted: list[str]
    settings: dict[str, Any]
    installed_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None


class PluginDataRead(BaseModel):
    """@brief Strictly typed view of a PluginData row."""

    model_config = ConfigDict(strict=True, from_attributes=True)

    id: UUID
    plugin_id: str
    community_id: UUID
    key: str
    value_json: Any
    created_at: datetime
    updated_at: datetime
