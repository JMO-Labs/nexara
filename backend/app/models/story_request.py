"""
@file story_request.py
@brief A member's request that another member tell a story (migration 0063).
"""

import uuid
from datetime import datetime, timedelta

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.user import COMMUNITY_DEFAULT

EXPIRY = timedelta(days=30)
"""@brief Lifetime of a request from creation."""

REMIND_AFTER = timedelta(days=14)
"""@brief Age at which the teller gets their single reminder."""


class StoryRequest(Base):
    """
    @brief Row in story_requests.

    ``declined`` is internal: the asker's API view shows it as ``open``
    until ``expires_at`` so a decline stays silent.
    """

    __tablename__ = "story_requests"
    __table_args__ = (
        CheckConstraint(
            "status IN ('open','answered','declined','expired')", name="story_requests_status_ck"
        ),
        CheckConstraint("char_length(question) <= 280", name="story_requests_question_ck"),
        Index("story_requests_teller_idx", "teller_id", "status"),
        Index("story_requests_asker_idx", "asker_id", "teller_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    community_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("communities.id", ondelete="CASCADE"),
        nullable=False,
        server_default=COMMUNITY_DEFAULT,
    )
    asker_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    teller_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="open")
    post_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("posts.id", ondelete="SET NULL")
    )
    reminded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now() + interval '30 days'"),
    )
