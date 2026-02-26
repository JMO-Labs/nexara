"""
@file invite.py
@brief Invite model for email-based user invitations.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.user import COMMUNITY_DEFAULT


class Invite(Base):
    """
    @brief Email invite tokens created by admins to onboard new users.
    """

    __tablename__ = "invites"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid(),
    )
    community_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("communities.id", ondelete="CASCADE"),
        nullable=False,
        server_default=COMMUNITY_DEFAULT,
    )
    email: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False, server_default="member")
    token_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False,
    )
    used_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"),
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
