"""
@file 0010_event_color.py
@brief Add nullable ``color`` column to ``events`` table.

Stores a per-event override hex color (#RRGGBB). NULL means use the default
(community / subgroup tone). Set/cleared by the event organizer via the
event create or update API.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "events",
        sa.Column("color", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("events", "color")
