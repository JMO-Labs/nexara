"""
@file community.py
@brief Community model — single-row table for multi-tenancy preparation.

Every community-scoped table references communities.id via community_id FK.
In v1 there is exactly one community per instance.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Community(Base):
    """
    @brief The root entity for multi-tenancy preparation.

    A single row is seeded on first migration. All community-scoped tables
    carry a community_id FK defaulting to the sentinel UUID.
    """

    __tablename__ = "communities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default="Nexara",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    sassybot_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    sassybot_sass_level: Mapped[int] = mapped_column(Integer, nullable=False, server_default="2")
    sassybot_probability: Mapped[int] = mapped_column(Integer, nullable=False, server_default="15")
    sassybot_invoke_only: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
