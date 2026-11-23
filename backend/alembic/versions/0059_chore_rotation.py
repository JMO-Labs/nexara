"""Chore rotation.

@file 0059_chore_rotation.py
@brief Add repeat, rotation, rotation_index, next_due_at to list_item.

Revision ID: 0059_chore_rotation
Revises: 0056_memorials
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0059_chore_rotation"
# ponytail: chained to 0056 in this worktree; orchestrator re-chains at merge.
down_revision = "0056_memorials"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """@brief Add the four chore columns, a check and a due-scan index."""
    op.add_column("list_item", sa.Column("repeat", sa.Text(), nullable=True))
    op.add_column(
        "list_item",
        sa.Column(
            "rotation",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=False,
            server_default=sa.text("'{}'::uuid[]"),
        ),
    )
    op.add_column(
        "list_item",
        sa.Column("rotation_index", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("list_item", sa.Column("next_due_at", sa.DateTime(timezone=True), nullable=True))
    op.create_check_constraint(
        "ck_list_item_repeat",
        "list_item",
        "repeat IS NULL OR repeat IN ('daily','weekly','monthly')",
    )
    op.create_index(
        "ix_list_item_next_due",
        "list_item",
        ["next_due_at"],
        postgresql_where=sa.text("repeat IS NOT NULL AND deleted_at IS NULL"),
    )


def downgrade() -> None:
    """@brief Drop index, check and columns."""
    op.drop_index("ix_list_item_next_due", table_name="list_item")
    op.drop_constraint("ck_list_item_repeat", "list_item", type_="check")
    op.drop_column("list_item", "next_due_at")
    op.drop_column("list_item", "rotation_index")
    op.drop_column("list_item", "rotation")
    op.drop_column("list_item", "repeat")
