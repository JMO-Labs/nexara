"""
@file expense.py
@brief Shared expense ledgers, members, expenses, shares and settlements
       (migration 0057). Money is integer cents.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import CHAR, Date, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.user import COMMUNITY_DEFAULT


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )


def _user_fk() -> Mapped[uuid.UUID]:
    return mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )


def _now() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ExpenseLedger(Base):
    """@brief Row in expense_ledgers; visible only to its members."""

    __tablename__ = "expense_ledgers"

    id: Mapped[uuid.UUID] = _uuid_pk()
    community_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("communities.id", ondelete="CASCADE"),
        nullable=False,
        server_default=COMMUNITY_DEFAULT,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    currency: Mapped[str] = mapped_column(CHAR(3), nullable=False)
    event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("events.id", ondelete="SET NULL")
    )
    wishlist_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("wishlists.id", ondelete="SET NULL")
    )
    created_by: Mapped[uuid.UUID] = _user_fk()
    created_at: Mapped[datetime] = _now()
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LedgerMember(Base):
    """@brief Row in ledger_members (composite pk)."""

    __tablename__ = "ledger_members"

    ledger_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("expense_ledgers.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )


class Expense(Base):
    """@brief Row in expenses; ``amount_cents`` > 0, soft-deleted via ``deleted_at``."""

    __tablename__ = "expenses"

    id: Mapped[uuid.UUID] = _uuid_pk()
    ledger_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("expense_ledgers.id", ondelete="CASCADE"), nullable=False
    )
    payer_id: Mapped[uuid.UUID] = _user_fk()
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    spent_on: Mapped[date] = mapped_column(Date, nullable=False)
    created_by: Mapped[uuid.UUID] = _user_fk()
    created_at: Mapped[datetime] = _now()
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ExpenseShare(Base):
    """@brief Row in expense_shares: one member's part of an expense."""

    __tablename__ = "expense_shares"

    expense_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("expenses.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)


class Settlement(Base):
    """@brief Row in settlements: ``from_user_id`` paid ``to_user_id``."""

    __tablename__ = "settlements"

    id: Mapped[uuid.UUID] = _uuid_pk()
    ledger_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("expense_ledgers.id", ondelete="CASCADE"), nullable=False
    )
    from_user_id: Mapped[uuid.UUID] = _user_fk()
    to_user_id: Mapped[uuid.UUID] = _user_fk()
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    created_by: Mapped[uuid.UUID] = _user_fk()
    created_at: Mapped[datetime] = _now()
