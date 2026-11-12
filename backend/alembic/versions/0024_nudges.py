"""add nudges table and nudge notification preferences

Revision ID: 0024_nudges
Revises: 0023_bookmarks
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "0024_nudges"
down_revision: str | Sequence[str] | None = "0023_bookmarks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_COMMUNITY = "00000000-0000-0000-0000-000000000001"


def upgrade() -> None:
    op.create_table(
        "nudges",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "community_id",
            UUID(as_uuid=True),
            sa.ForeignKey("communities.id", ondelete="CASCADE"),
            nullable=False,
            server_default=DEFAULT_COMMUNITY,
        ),
        sa.Column(
            "sender_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "target_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("nudge_type", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("nudge_type IN ('user_initiated', 'gentle')", name="ck_nudges_type"),
    )
    op.create_index("ix_nudges_pair_created", "nudges", ["sender_id", "target_id", "created_at"])
    op.create_index(
        "ix_nudges_target_type_created", "nudges", ["target_id", "nudge_type", "created_at"]
    )
    for col, default in (
        ("notif_nudge_inapp", "true"),
        ("notif_nudge_push", "false"),
        ("notif_nudge_email", "false"),
        ("receive_gentle_nudges", "true"),
    ):
        op.add_column(
            "user_settings",
            sa.Column(col, sa.Boolean(), nullable=False, server_default=default),
        )


def downgrade() -> None:
    for col in (
        "receive_gentle_nudges",
        "notif_nudge_email",
        "notif_nudge_push",
        "notif_nudge_inapp",
    ):
        op.drop_column("user_settings", col)
    op.drop_index("ix_nudges_target_type_created", table_name="nudges")
    op.drop_index("ix_nudges_pair_created", table_name="nudges")
    op.drop_table("nudges")
