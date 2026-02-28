"""
@file base.py
@brief SQLAlchemy declarative base with common column mixins.

All application models inherit from Base. The TimestampMixin provides
created_at / updated_at columns automatically.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """
    @brief Declarative base for all SQLAlchemy models.

    Provides a shared metadata registry. All models must inherit from this.
    """

    pass


class TimestampMixin:
    """
    @brief Mixin providing created_at and updated_at columns.

    updated_at is set by a Postgres trigger (see migration) so we only set
    server_default here. The trigger handles subsequent updates.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class UUIDPrimaryKeyMixin:
    """
    @brief Mixin providing a UUID primary key with database-side generation.
    """

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
