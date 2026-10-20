"""
@file 0012_event_geo.py
@brief Add nullable ``latitude``/``longitude`` columns to ``events``.

Stores geocoded coordinates for the location string. Populated when the
user picks a Photon autocomplete suggestion in the event modal. NULL
means free-text location with no resolved coords (no map embed).
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("events", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("events", sa.Column("longitude", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("events", "longitude")
    op.drop_column("events", "latitude")
