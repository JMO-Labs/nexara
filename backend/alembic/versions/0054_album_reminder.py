"""Event album reminder stamp.

@file 0054_album_reminder.py
@brief Add events.album_reminded_at so the reminder fires once per event.

Revision ID: 0054_album_reminder
Revises: 0053_recap_settings
"""

import sqlalchemy as sa

from alembic import op

revision = "0054_album_reminder"
down_revision = "0053_recap_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """@brief Add the nullable reminder stamp."""
    op.add_column(
        "events", sa.Column("album_reminded_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    """@brief Drop the stamp."""
    op.drop_column("events", "album_reminded_at")
