"""Event rides: offers, requests and passengers.

@file 0058_event_rides.py
@brief Add event_rides and ride_passengers.

Revision ID: 0058_event_rides
Revises: 0056_memorials
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0058_event_rides"
down_revision = "0057_expenses"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """@brief Create both tables and lookup indexes."""
    op.create_table(
        "event_rides",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "community_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("communities.id", ondelete="CASCADE"),
            nullable=False,
            server_default=sa.text("'00000000-0000-0000-0000-000000000001'::uuid"),
        ),
        sa.Column(
            "event_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("seats", sa.Integer(), nullable=False),
        sa.Column("origin", sa.Text(), nullable=False, server_default=""),
        sa.Column("depart_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("kind IN ('offer','request')", name="event_rides_kind_ck"),
        sa.CheckConstraint("seats BETWEEN 1 AND 8", name="event_rides_seats_ck"),
        sa.CheckConstraint("char_length(origin) <= 120", name="event_rides_origin_ck"),
        sa.CheckConstraint("char_length(note) <= 200", name="event_rides_note_ck"),
    )
    op.create_index(
        "ix_event_rides_event",
        "event_rides",
        ["event_id"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_table(
        "ride_passengers",
        sa.Column(
            "ride_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("event_rides.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("seats", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("seats BETWEEN 1 AND 8", name="ride_passengers_seats_ck"),
    )
    op.create_index("ix_ride_passengers_user", "ride_passengers", ["user_id"])


def downgrade() -> None:
    """@brief Drop both tables."""
    op.drop_index("ix_ride_passengers_user", table_name="ride_passengers")
    op.drop_table("ride_passengers")
    op.drop_index("ix_event_rides_event", table_name="event_rides")
    op.drop_table("event_rides")
