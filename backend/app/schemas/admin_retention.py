"""
@file admin_retention.py
@brief Schemas for the admin retention policy endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RetentionUpdate(BaseModel):
    """@brief Editable fields of a policy; ``retention_days`` null = keep forever."""

    enabled: bool
    retention_days: int | None = Field(default=None, ge=1)
    delete_media_files: bool


class RetentionPolicyOut(BaseModel):
    """@brief Retention policy as returned to the admin UI."""

    model_config = ConfigDict(from_attributes=True)

    policy_key: str
    enabled: bool
    retention_days: int | None
    delete_media_files: bool
    updated_at: datetime
    updated_by: uuid.UUID | None
