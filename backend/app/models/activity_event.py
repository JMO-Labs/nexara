"""
@file activity_event.py
@brief ActivityEvent model for community-wide activity feed logging.

Append-only log of domain events (post created, media uploaded, RSVP cast, etc.)
read by ActivityRepository and aggregated for the home activity feed. No soft-delete;
use is_active flag instead.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, Index, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base
from app.models.user import COMMUNITY_DEFAULT


class ActivityEvent(Base):
    """
    @brief Append-only log of community-wide domain events.

    Tracks verbs like 'post.created', 'media.uploaded', 'event.rsvp' for
    activity feed aggregation. No FK on object_id (heterogeneous types);
    use invalidate() to mark deleted objects as is_active=false.
    """

    __tablename__ = "activity_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    community_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        server_default=COMMUNITY_DEFAULT,
        index=True,
    )
    actor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    verb: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    object_type: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    object_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    target_type: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    target_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    subgroup_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    visibility: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default="community",
    )
    event_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default="{}",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
    )
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        # Feed index: community + created_at DESC, filtered by is_active
        Index(
            "activity_event_feed_idx",
            community_id,
            created_at.desc(),
            postgresql_where=(is_active.is_(True)),
        ),
        # Subgroup index: community + subgroup + created_at DESC, filtered by is_active
        Index(
            "activity_event_subgroup_idx",
            community_id,
            subgroup_id,
            created_at.desc(),
            postgresql_where=(is_active.is_(True)),
        ),
        # Object index: object_type + object_id (for invalidate() lookups)
        Index(
            "activity_event_object_idx",
            object_type,
            object_id,
        ),
    )
