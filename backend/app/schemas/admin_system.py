"""
@file admin_system.py
@brief Response schemas for GET /admin/system (no secrets, no connection strings).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class Component(BaseModel):
    """@brief One monitored component."""

    name: str
    status: Literal["ok", "warn", "down"]
    detail: str = ""


class TableSize(BaseModel):
    """@brief A table and its total size in bytes."""

    name: str
    bytes: int


class DiskInfo(BaseModel):
    """@brief Storage usage; ``used_pct`` is None for external (S3) storage."""

    external: bool
    total_bytes: int | None = None
    used_bytes: int | None = None
    used_pct: float | None = None
    db_bytes: int | None = None
    top_tables: list[TableSize] = []


class RuntimeInfo(BaseModel):
    """@brief Process / host runtime facts."""

    version: str
    alembic_head: str | None = None
    uptime_seconds: int
    cpu_percent: float
    mem_total_bytes: int
    mem_used_bytes: int
    mem_limit_bytes: int | None = None


class SystemHealth(BaseModel):
    """@brief Full system health snapshot."""

    components: list[Component]
    disk: DiskInfo
    runtime: RuntimeInfo
