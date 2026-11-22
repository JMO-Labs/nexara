"""household: family members and pets without accounts; taggable

Revision ID: 0037_household
Revises: 0036_tags
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision: str = "0037_household"
down_revision: str | Sequence[str] | None = "0036_tags"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """@brief Create household_members; allow them as tag subjects."""
    op.create_table(
        "household_members",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "community_id",
            UUID(as_uuid=True),
            sa.ForeignKey("communities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "owner_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("relation", sa.Text()),
        sa.Column("birthday", sa.Date()),
        sa.Column("show_birth_year", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "photo_media_id", UUID(as_uuid=True), sa.ForeignKey("media.id", ondelete="SET NULL")
        ),
        sa.Column("visibility", sa.Text(), nullable=False, server_default="groups"),
        sa.Column("bio", sa.Text()),
        sa.Column("species", sa.Text()),
        sa.Column("breed", sa.Text()),
        sa.Column("gotcha_day", sa.Date()),
        sa.Column("likes", JSONB(), nullable=False, server_default="[]"),
        sa.Column("dislikes", JSONB(), nullable=False, server_default="[]"),
        sa.Column("care_card", sa.Text()),
        sa.Column("care_visibility", sa.Text(), nullable=False, server_default="private"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("kind IN ('person','pet')", name="household_kind_ck"),
        sa.CheckConstraint(
            "visibility IN ('private','groups','community')", name="household_visibility_ck"
        ),
        sa.CheckConstraint(
            "care_visibility IN ('private','groups','community')", name="household_care_ck"
        ),
    )
    op.create_index("household_owner_idx", "household_members", ["owner_id"])
    op.drop_constraint("tags_subject_type_ck", "tags", type_="check")
    op.create_check_constraint(
        "tags_subject_type_ck", "tags", "subject_type IN ('user','household')"
    )


def downgrade() -> None:
    """@brief Drop household tags and the table."""
    op.execute("DELETE FROM tags WHERE subject_type = 'household'")
    op.drop_constraint("tags_subject_type_ck", "tags", type_="check")
    op.create_check_constraint("tags_subject_type_ck", "tags", "subject_type IN ('user')")
    op.drop_table("household_members")
