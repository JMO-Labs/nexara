"""Reconnect nudges: settings, snoozes and the new nudge type.

@file 0061_reconnect.py
@brief Add user_settings.reconnect_nudges/reconnect_days, reconnect_snoozes,
       and allow nudge_type 'reconnect'.

Revision ID: 0061_reconnect
Revises: 0060_relations
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0061_reconnect"
down_revision = "0060_relations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """@brief Add settings columns, snooze table and widen the nudge-type check."""
    op.add_column(
        "user_settings",
        sa.Column("reconnect_nudges", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.add_column(
        "user_settings",
        sa.Column("reconnect_days", sa.SmallInteger(), nullable=False, server_default="30"),
    )
    op.create_check_constraint(
        "ck_user_settings_reconnect_days", "user_settings", "reconnect_days IN (14, 30, 60, 90)"
    )
    op.create_table(
        "reconnect_snoozes",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "target_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("until", sa.DateTime(timezone=True), nullable=False),
    )
    op.drop_constraint("ck_nudges_type", "nudges", type_="check")
    op.create_check_constraint(
        "ck_nudges_type", "nudges", "nudge_type IN ('user_initiated', 'gentle', 'reconnect')"
    )


def downgrade() -> None:
    """@brief Reverse :func:`upgrade` (reconnect nudge rows are removed)."""
    op.execute("DELETE FROM nudges WHERE nudge_type = 'reconnect'")
    op.drop_constraint("ck_nudges_type", "nudges", type_="check")
    op.create_check_constraint(
        "ck_nudges_type", "nudges", "nudge_type IN ('user_initiated', 'gentle')"
    )
    op.drop_table("reconnect_snoozes")
    op.drop_constraint("ck_user_settings_reconnect_days", "user_settings", type_="check")
    op.drop_column("user_settings", "reconnect_days")
    op.drop_column("user_settings", "reconnect_nudges")
