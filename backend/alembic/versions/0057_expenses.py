"""Shared expenses.

@file 0057_expenses.py
@brief Add expense_ledgers, ledger_members, expenses, expense_shares, settlements.

Revision ID: 0057_expenses
Revises: 0056_memorials
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0057_expenses"
down_revision = "0056_memorials"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)
_ID = {"server_default": sa.text("gen_random_uuid()")}
_NOW = {"server_default": sa.func.now(), "nullable": False}


def _fk(col: str, table: str, **kw: object) -> sa.Column:
    return sa.Column(col, _UUID, sa.ForeignKey(f"{table}.id", ondelete="CASCADE"), **kw)


def upgrade() -> None:
    """@brief Create the five expense tables."""
    op.create_table(
        "expense_ledgers",
        sa.Column("id", _UUID, primary_key=True, **_ID),
        _fk(
            "community_id",
            "communities",
            nullable=False,
            server_default="00000000-0000-0000-0000-000000000001",
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("currency", sa.CHAR(3), nullable=False),
        sa.Column("event_id", _UUID, sa.ForeignKey("events.id", ondelete="SET NULL")),
        sa.Column("wishlist_id", _UUID, sa.ForeignKey("wishlists.id", ondelete="SET NULL")),
        _fk("created_by", "users", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), **_NOW),
        sa.Column("archived_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("char_length(name) <= 80", name="expense_ledgers_name_len"),
    )
    op.create_index("expense_ledgers_event_idx", "expense_ledgers", ["event_id"])
    op.create_index("expense_ledgers_wishlist_idx", "expense_ledgers", ["wishlist_id"])
    op.create_table(
        "ledger_members",
        _fk("ledger_id", "expense_ledgers", primary_key=True),
        _fk("user_id", "users", primary_key=True),
    )
    op.create_index("ledger_members_user_idx", "ledger_members", ["user_id"])
    op.create_table(
        "expenses",
        sa.Column("id", _UUID, primary_key=True, **_ID),
        _fk("ledger_id", "expense_ledgers", nullable=False),
        _fk("payer_id", "users", nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("spent_on", sa.Date(), nullable=False),
        _fk("created_by", "users", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), **_NOW),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("amount_cents > 0", name="expenses_amount_pos"),
        sa.CheckConstraint("char_length(description) <= 200", name="expenses_desc_len"),
    )
    op.create_index("expenses_ledger_idx", "expenses", ["ledger_id"])
    op.create_table(
        "expense_shares",
        _fk("expense_id", "expenses", primary_key=True),
        _fk("user_id", "users", primary_key=True),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.CheckConstraint("amount_cents >= 0", name="expense_shares_amount_nonneg"),
    )
    op.create_table(
        "settlements",
        sa.Column("id", _UUID, primary_key=True, **_ID),
        _fk("ledger_id", "expense_ledgers", nullable=False),
        _fk("from_user_id", "users", nullable=False),
        _fk("to_user_id", "users", nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        _fk("created_by", "users", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), **_NOW),
        sa.CheckConstraint("amount_cents > 0", name="settlements_amount_pos"),
    )
    op.create_index("settlements_ledger_idx", "settlements", ["ledger_id"])


def downgrade() -> None:
    """@brief Drop the tables in dependency order."""
    op.drop_table("settlements")
    op.drop_table("expense_shares")
    op.drop_table("expenses")
    op.drop_table("ledger_members")
    op.drop_table("expense_ledgers")
