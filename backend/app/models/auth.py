"""
@file auth.py
@brief Authentication models: RefreshToken and UserBackupCode.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import INET, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RefreshToken(Base):
    """
    @brief Refresh token records for JWT rotation.

    Tokens are stored as hashes. The family_id groups tokens from
    the same refresh chain to detect reuse attacks.
    """

    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid(),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    family_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    ip_address: Mapped[str | None] = mapped_column(INET)
    user_agent: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        Index("refresh_tokens_user_idx", "user_id"),
        Index("refresh_tokens_family_idx", "family_id"),
    )


class UserBackupCode(Base):
    """
    @brief 2FA backup codes stored as hashes.
    """

    __tablename__ = "user_backup_codes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid(),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    code_hash: Mapped[str] = mapped_column(Text, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
