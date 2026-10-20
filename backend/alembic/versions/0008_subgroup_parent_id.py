"""
@file 0008_subgroup_parent_id.py
@brief Add ``parent_id`` self-FK to subgroups for parent/child hierarchy.

Allows a group to inherit from another group within the same community.
``ondelete=SET NULL`` so deleting a parent does not cascade-remove its
children — they simply orphan up to the root.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "subgroups",
        sa.Column(
            "parent_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("subgroups.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("subgroups_parent_idx", "subgroups", ["parent_id"])


def downgrade() -> None:
    op.drop_index("subgroups_parent_idx", table_name="subgroups")
    op.drop_column("subgroups", "parent_id")
