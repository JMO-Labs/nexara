"""Recap email preferences.

@file 0053_recap_settings.py
@brief Add user_settings.recap_cadence and recap_last_sent_at.

Revision ID: 0053_recap_settings
Revises: 0052_time_capsules
"""

import sqlalchemy as sa

from alembic import op

revision = "0053_recap_settings"
down_revision = "0052_time_capsules"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """@brief Add the cadence (default weekly) and last-sent stamp."""
    op.add_column(
        "user_settings",
        sa.Column("recap_cadence", sa.Text(), nullable=False, server_default="weekly"),
    )
    op.create_check_constraint(
        "ck_user_settings_recap_cadence",
        "user_settings",
        "recap_cadence IN ('weekly','monthly','off')",
    )
    op.add_column(
        "user_settings",
        sa.Column("recap_last_sent_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """@brief Remove both columns."""
    op.drop_column("user_settings", "recap_last_sent_at")
    op.drop_constraint("ck_user_settings_recap_cadence", "user_settings", type_="check")
    op.drop_column("user_settings", "recap_cadence")
