"""
@file retention.py
@brief Data retention models: RetentionPolicy, StorageSnapshot, StorageAlert.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RetentionPolicy(Base):
    """@brief Admin-tunable retention settings; one row per policy key."""

    __tablename__ = "retention_policies"

    policy_key: Mapped[str] = mapped_column(Text, primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    retention_days: Mapped[int | None] = mapped_column(Integer)
    delete_media_files: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"),
    )


class StorageSnapshot(Base):
    """@brief Daily storage usage snapshots for trend charts and alerting."""

    __tablename__ = "storage_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid(),
    )
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False, unique=True)
    media_images_bytes: Mapped[int | None] = mapped_column(BigInteger)
    media_videos_bytes: Mapped[int | None] = mapped_column(BigInteger)
    media_thumbnails_bytes: Mapped[int | None] = mapped_column(BigInteger)
    media_other_bytes: Mapped[int | None] = mapped_column(BigInteger)
    db_estimated_bytes: Mapped[int | None] = mapped_column(BigInteger)
    total_bytes: Mapped[int | None] = mapped_column(BigInteger)
    total_media_files: Mapped[int | None] = mapped_column(Integer)
    total_posts: Mapped[int | None] = mapped_column(Integer)
    total_users: Mapped[int | None] = mapped_column(Integer)
    total_messages: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    __table_args__ = (
        Index("storage_snapshots_date_idx", snapshot_date.desc()),
    )


class StorageAlert(Base):
    """@brief Open threshold alerts for disk usage warnings."""

    __tablename__ = "storage_alerts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid(),
    )
    alert_type: Mapped[str] = mapped_column(Text, nullable=False)
    fired_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    disk_used_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    bytes_used: Mapped[int | None] = mapped_column(BigInteger)
    bytes_total: Mapped[int | None] = mapped_column(BigInteger)
