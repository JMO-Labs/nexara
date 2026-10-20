"""add events.contribution_slots JSONB column

Revision ID: 0007
Revises: 0006
Create Date: 2026-04-25 00:00:00.000000

Adds a ``contribution_slots`` JSONB column on the ``events`` table to support
the "who's bringing what" contribution planner. Each row is an array of
slot objects ``{id, title, quantity_needed, quantity_claimed, claimed_by}``.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """@brief Add contribution_slots JSONB column to events."""
    op.add_column(
        "events",
        sa.Column(
            "contribution_slots",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    """@brief Drop contribution_slots column."""
    op.drop_column("events", "contribution_slots")
