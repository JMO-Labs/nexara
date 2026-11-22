"""Memorials.

@file 0056_memorials.py
@brief Add household_members.passed_on, users.memorialized_at, users.passed_on.

Revision ID: 0056_memorials
Revises: 0053_recap_settings
"""

import sqlalchemy as sa

from alembic import op

revision = "0056_memorials"
# ponytail: chained to 0053 in this worktree; orchestrator re-chains at merge.
down_revision = "0055_recipes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """@brief Add the three nullable memorial columns."""
    op.add_column("household_members", sa.Column("passed_on", sa.Date(), nullable=True))
    op.add_column("users", sa.Column("memorialized_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("passed_on", sa.Date(), nullable=True))


def downgrade() -> None:
    """@brief Remove the columns."""
    op.drop_column("users", "passed_on")
    op.drop_column("users", "memorialized_at")
    op.drop_column("household_members", "passed_on")
