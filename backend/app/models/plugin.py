"""
@file plugin.py
@brief Plugin installation state and key-value plugin data models.

Plugins are installed independently per community. Uninstall is a soft
delete (deleted_at); rows are never removed.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.user import COMMUNITY_DEFAULT


class Plugin(Base):
    """
    @brief A plugin installed in a community.

    The primary key is (id, community_id) so the same plugin id can be
    installed independently in several communities.
    """

    __tablename__ = "plugins"
    __table_args__ = (
        Index("ix_plugins_id_community", "id", "community_id"),
        Index("ix_plugins_deleted_at", "deleted_at"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    community_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("communities.id", ondelete="CASCADE"),
        primary_key=True,
        server_default=COMMUNITY_DEFAULT,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    permissions_granted: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    settings: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    pending_manifest: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    installed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PluginData(Base):
    """@brief Arbitrary per-plugin JSON key-value storage."""

    __tablename__ = "plugin_data"
    __table_args__ = (
        ForeignKeyConstraint(
            ["plugin_id", "community_id"],
            ["plugins.id", "plugins.community_id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint("plugin_id", "community_id", "key", name="uq_plugin_data_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    plugin_id: Mapped[str] = mapped_column(Text, nullable=False)
    community_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, server_default=COMMUNITY_DEFAULT
    )
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    value_json: Mapped[Any] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class PluginApiKey(Base):
    """@brief Narrow-scope API key for a plugin (bcrypt-hashed, never plaintext)."""

    __tablename__ = "plugin_api_keys"
    __table_args__ = (
        ForeignKeyConstraint(
            ["plugin_id", "community_id"],
            ["plugins.id", "plugins.community_id"],
            ondelete="CASCADE",
        ),
        Index("ix_plugin_api_keys_plugin", "plugin_id", "community_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    plugin_id: Mapped[str] = mapped_column(Text, nullable=False)
    community_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, server_default=COMMUNITY_DEFAULT
    )
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    key_hint: Mapped[str] = mapped_column(String(8), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
