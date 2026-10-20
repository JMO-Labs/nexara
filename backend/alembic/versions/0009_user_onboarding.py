"""
@file 0009_user_onboarding.py
@brief Add ``tour_completed_at`` TIMESTAMP to users table for onboarding tracking.

Allows tracking whether a user has completed the guided onboarding tour.
``NULL`` means tour not yet started or completed.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("tour_completed_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "tour_completed_at")
