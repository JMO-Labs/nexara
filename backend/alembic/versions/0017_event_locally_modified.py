"""event: add locally_modified flag

Revision ID: 0017_event_locally_modified
Revises: 0016_gallery_cover_backfill
"""
from alembic import op
import sqlalchemy as sa


revision = "0017_event_locally_modified"
down_revision = "0016_gallery_cover_backfill"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "events",
        sa.Column(
            "locally_modified",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("events", "locally_modified")
