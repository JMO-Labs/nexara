"""
@file calendar.py
@brief Calendar entity — owner of events.

Each event belongs to exactly one Calendar. Three kinds:
- ``personal``: owned by a user (auto-created on registration)
- ``community``: one per community (visible to all members)
- ``subgroup``: one per subgroup (visible to subgroup members)

Future: external_provider/external_id support iCal/Google Calendar feeds.
This is distinct from :class:`CalendarSubscription` (legacy iCal feed import)
and supersedes the per-event ``visibility`` column long-term.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.user import COMMUNITY_DEFAULT


class Calendar(Base):
    """@brief A named calendar that owns a set of events."""

    __tablename__ = "calendars"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    community_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("communities.id", ondelete="CASCADE"),
        nullable=False,
        server_default=COMMUNITY_DEFAULT,
    )
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    """One of: ``personal``, ``community``, ``subgroup``."""

    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
    )
    subgroup_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subgroups.id", ondelete="CASCADE"),
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    color: Mapped[str | None] = mapped_column(Text)
    external_provider: Mapped[str | None] = mapped_column(Text)
    external_id: Mapped[str | None] = mapped_column(Text)

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
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint(
            "kind IN ('personal', 'community', 'subgroup')",
            name="calendars_kind_check",
        ),
        CheckConstraint(
            "(kind = 'personal' AND owner_id IS NOT NULL AND subgroup_id IS NULL) OR "
            "(kind = 'subgroup' AND subgroup_id IS NOT NULL AND owner_id IS NULL) OR "
            "(kind = 'community' AND owner_id IS NULL AND subgroup_id IS NULL)",
            name="calendars_kind_fk_check",
        ),
        Index(
            "calendars_one_personal_per_user",
            "community_id",
            "owner_id",
            unique=True,
            postgresql_where=(owner_id.isnot(None)),
        ),
        Index(
            "calendars_one_per_subgroup",
            "community_id",
            "subgroup_id",
            unique=True,
            postgresql_where=(subgroup_id.isnot(None)),
        ),
        Index(
            "calendars_one_community_per_community",
            "community_id",
            unique=True,
            postgresql_where=(
                "kind = 'community' AND deleted_at IS NULL"
            ),
        ),
        Index("calendars_owner_idx", "owner_id"),
        Index("calendars_subgroup_idx", "subgroup_id"),
        Index("calendars_community_kind_idx", "community_id", "kind"),
    )
