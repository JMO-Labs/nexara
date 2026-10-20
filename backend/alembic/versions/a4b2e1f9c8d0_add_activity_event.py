"""add_activity_event: activity feed table with indexes

Revision ID: a4b2e1f9c8d0
Revises: 9f8ff6e495e4
Create Date: 2026-04-30 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a4b2e1f9c8d0"
down_revision: str | None = "9f8ff6e495e4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create activity_events table with indexes."""
    op.create_table(
        "activity_events",
        sa.Column(
            "id", UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "community_id",
            UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("'00000000-0000-0000-0000-000000000001'::uuid"),
        ),
        sa.Column("actor_id", UUID(as_uuid=True), nullable=False),
        sa.Column("verb", sa.Text(), nullable=False),
        sa.Column("object_type", sa.Text(), nullable=False),
        sa.Column("object_id", UUID(as_uuid=True), nullable=False),
        sa.Column("target_type", sa.Text(), nullable=True),
        sa.Column("target_id", UUID(as_uuid=True), nullable=True),
        sa.Column("subgroup_id", UUID(as_uuid=True), nullable=True),
        sa.Column("visibility", sa.Text(), nullable=False, server_default="community"),
        sa.Column("metadata", JSONB(), nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes as specified in the schema
    op.create_index(
        "activity_event_feed_idx",
        "activity_events",
        [sa.text("community_id"), sa.text("created_at DESC")],
        postgresql_where=sa.text("is_active"),
    )

    op.create_index(
        "activity_event_subgroup_idx",
        "activity_events",
        [sa.text("community_id"), sa.text("subgroup_id"), sa.text("created_at DESC")],
        postgresql_where=sa.text("is_active"),
    )

    op.create_index(
        "activity_event_object_idx",
        "activity_events",
        [sa.text("object_type"), sa.text("object_id")],
    )

    # Additional indexes for filter columns
    op.create_index(
        "ix_activity_events_community_id",
        "activity_events",
        ["community_id"],
    )

    op.create_index(
        "ix_activity_events_actor_id",
        "activity_events",
        ["actor_id"],
    )

    op.create_index(
        "ix_activity_events_subgroup_id",
        "activity_events",
        ["subgroup_id"],
    )


def downgrade() -> None:
    """Drop activity_events table and indexes."""
    op.drop_index("ix_activity_events_subgroup_id", table_name="activity_events")
    op.drop_index("ix_activity_events_actor_id", table_name="activity_events")
    op.drop_index("ix_activity_events_community_id", table_name="activity_events")
    op.drop_index("activity_event_object_idx", table_name="activity_events")
    op.drop_index("activity_event_subgroup_idx", table_name="activity_events")
    op.drop_index("activity_event_feed_idx", table_name="activity_events")
    op.drop_table("activity_events")
