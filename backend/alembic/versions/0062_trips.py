"""Safe-arrival trips and their watchers.

@file 0062_trips.py
@brief Add trips and trip_watchers (no location columns, by design).

Revision ID: 0062_trips
Revises: 0059_chore_rotation
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0062_trips"
down_revision = "0059_chore_rotation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """@brief Create both tables, the one-active-trip index and the sweep index."""
    op.create_table(
        "trips",
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
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("expected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("arrived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("alerted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("char_length(label) BETWEEN 1 AND 80", name="trips_label_ck"),
    )
    op.create_index(
        "uq_trips_one_active",
        "trips",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("arrived_at IS NULL AND ended_at IS NULL"),
    )
    op.create_index(
        "ix_trips_sweep",
        "trips",
        ["expected_at"],
        postgresql_where=sa.text("arrived_at IS NULL AND ended_at IS NULL"),
    )
    op.create_table(
        "trip_watchers",
        sa.Column(
            "trip_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("trips.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("trip_id", "user_id"),
    )
    op.create_index("ix_trip_watchers_user", "trip_watchers", ["user_id"])


def downgrade() -> None:
    """@brief Drop both tables."""
    op.drop_index("ix_trip_watchers_user", table_name="trip_watchers")
    op.drop_table("trip_watchers")
    op.drop_index("ix_trips_sweep", table_name="trips")
    op.drop_index("uq_trips_one_active", table_name="trips")
    op.drop_table("trips")
