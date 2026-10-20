"""event: add original_start for exception occurrences

Revision ID: 0015_event_original_start
Revises: 0014_prompt_interest
"""

import sqlalchemy as sa

from alembic import op

revision = "0015_event_original_start"
down_revision = "0014_prompt_interest"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "events",
        sa.Column("original_start", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("events", "original_start")
