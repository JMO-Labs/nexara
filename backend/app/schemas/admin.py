"""
@file admin.py
@brief Pydantic schemas for admin panel API endpoints.

Defines metrics, audit log, settings, and user management payloads.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class CommunityMetrics(BaseModel):
    """@brief Community-level activity and user metrics."""

    users_total: int
    users_active_30d: int
    users_online_now: int
    posts_total: int
    posts_last_7d: int
    media_files: int
    media_storage_bytes: int


class SystemMetrics(BaseModel):
    """@brief System health and infrastructure metrics."""

    version: str
    uptime_seconds: float
    db_size_bytes: int | None = None
    valkey_memory_bytes: int | None = None
    celery_queue_depth: int | None = None


class WafMetrics(BaseModel):
    """@brief WAF block statistics."""

    blocks_today: int
    blocks_by_reason: dict[str, int]


class MetricsResponse(BaseModel):
    """@brief Combined metrics response for admin dashboard."""

    community: CommunityMetrics
    system: SystemMetrics
    waf: WafMetrics


class AuditLogEntry(BaseModel):
    """@brief Single audit log entry for admin listing."""

    id: UUID
    actor_id: UUID | None
    actor_display_name: str | None = None
    action: str
    target_type: str | None
    target_id: UUID | None
    target_display: str | None = None
    extra_data: dict[str, Any] | None
    ip_address: str | None
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("ip_address", mode="before")
    @classmethod
    def _coerce_ip_to_str(cls, v: Any) -> str | None:
        """@brief Coerce PostgreSQL INET (IPv4Address/IPv6Address) to string."""
        if v is None:
            return None
        return str(v)


class AdminSettingsResponse(BaseModel):
    """@brief Admin-configurable global settings."""

    enable_registration: bool
    require_invite: bool
    storage_quota_default: int
    waf_enabled: bool


class AdminSettingsUpdate(BaseModel):
    """@brief Partial update payload for admin settings."""

    enable_registration: bool | None = None
    require_invite: bool | None = None
    storage_quota_default: int | None = None
    waf_enabled: bool | None = None


class UserRoleUpdate(BaseModel):
    """@brief Payload for changing a user's role."""

    role: str = Field(..., pattern=r"^(admin|member|viewer)$")


class AdminUserListItem(BaseModel):
    """
    @brief Admin user list item with status for user management table.

    Extends user fields with status derived from is_active.
    """

    id: UUID
    username: str
    display_name: str
    email: str
    avatar_url: str | None = None
    bio: str | None = None
    title: str | None = None
    location: str | None = None
    website_url: str | None = None
    role: str
    created_at: datetime
    last_seen_at: datetime | None = None
    status: str = "active"
