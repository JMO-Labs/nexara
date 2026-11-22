"""list_assignments: item assignments (take/assign/accept) and list activity log

Revision ID: 0043_list_assignments
Revises: 0042_wishlists_v2
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "0043_list_assignments"
down_revision: str | Sequence[str] | None = "0042_wishlists_v2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

COMMUNITY = sa.text("'00000000-0000-0000-0000-000000000001'::uuid")


def _base() -> list[sa.Column]:  # type: ignore[type-arg]
    return [
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "community_id",
            UUID(as_uuid=True),
            sa.ForeignKey("communities.id", ondelete="CASCADE"),
            nullable=False,
            server_default=COMMUNITY,
        ),
    ]


def upgrade() -> None:
    """@brief Create list_item_assignments and list_activity."""
    op.create_table(
        "list_item_assignments",
        *_base(),
        sa.Column(
            "item_id",
            UUID(as_uuid=True),
            sa.ForeignKey("list_item.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "list_id",
            UUID(as_uuid=True),
            sa.ForeignKey("list.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "assignee_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "assigned_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("responded_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "status IN ('pending','accepted','declined')", name="ck_list_item_assignment_status"
        ),
    )
    op.create_index(
        "uq_list_item_assignment_active",
        "list_item_assignments",
        ["item_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('pending','accepted')"),
    )
    op.create_index("ix_list_item_assignments_list", "list_item_assignments", ["list_id"])
    op.create_table(
        "list_activity",
        *_base(),
        sa.Column(
            "list_id",
            UUID(as_uuid=True),
            sa.ForeignKey("list.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("item_id", UUID(as_uuid=True)),
        sa.Column("item_title", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "actor_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("target_user_id", UUID(as_uuid=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index(
        "ix_list_activity_list_created", "list_activity", ["list_id", sa.text("created_at DESC")]
    )


def downgrade() -> None:
    """@brief Drop both tables."""
    op.drop_table("list_activity")
    op.drop_table("list_item_assignments")
