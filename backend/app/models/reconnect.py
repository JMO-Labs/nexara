"""
@file reconnect.py
@brief ReconnectSnooze: a user muting reconnect reminders about one person
       (migration 0061).
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ReconnectSnooze(Base):
    """@brief ``user_id`` will not be reminded about ``target_id`` until ``until``."""

    __tablename__ = "reconnect_snoozes"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    target_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
