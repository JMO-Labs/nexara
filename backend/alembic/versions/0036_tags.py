"""tags: people tagged in posts, comments and photos

Revision ID: 0036_tags
Revises: 0035_profile_fields
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "0036_tags"
down_revision: str | Sequence[str] | None = "0035_profile_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """@brief Create the polymorphic tags table."""
    op.create_table(
        "tags",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "community_id",
            UUID(as_uuid=True),
            sa.ForeignKey("communities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("target_type", sa.Text(), nullable=False),
        sa.Column("target_id", UUID(as_uuid=True), nullable=False),
        sa.Column("subject_type", sa.Text(), nullable=False, server_default="user"),
        sa.Column("subject_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "tagged_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("target_type IN ('post','comment','media')", name="tags_target_type_ck"),
        sa.CheckConstraint("subject_type IN ('user')", name="tags_subject_type_ck"),
        sa.UniqueConstraint(
            "target_type", "target_id", "subject_type", "subject_id", name="tags_unique"
        ),
    )
    op.create_index("tags_target_idx", "tags", ["target_type", "target_id"])
    op.create_index("tags_subject_idx", "tags", ["subject_type", "subject_id", "created_at"])


def downgrade() -> None:
    """@brief Drop the tags table."""
    op.drop_table("tags")
