"""home glass bento: chat_reads table, home_pattern, reduce_transparency

Revision ID: 0032_home_glass_bento
Revises: 0030_list_notif_email_defaults
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0032_home_glass_bento"
down_revision: str | Sequence[str] | None = "0030_list_notif_email_defaults"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COMMUNITY = "00000000-0000-0000-0000-000000000001"


def upgrade() -> None:
    op.create_table(
        "chat_reads",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "channel_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chat_channels.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "community_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("communities.id", ondelete="CASCADE"),
            nullable=False,
            server_default=_COMMUNITY,
        ),
        sa.Column("last_read_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_chat_reads_user_id", "chat_reads", ["user_id"])
    op.add_column("user_settings", sa.Column("home_pattern", sa.Text(), nullable=True))
    op.add_column(
        "user_settings",
        sa.Column(
            "reduce_transparency", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
    )
    op.add_column(
        "community_branding",
        sa.Column("home_pattern", sa.Text(), nullable=False, server_default="contour"),
    )


def downgrade() -> None:
    op.drop_column("community_branding", "home_pattern")
    op.drop_column("user_settings", "reduce_transparency")
    op.drop_column("user_settings", "home_pattern")
    op.drop_index("ix_chat_reads_user_id", table_name="chat_reads")
    op.drop_table("chat_reads")
