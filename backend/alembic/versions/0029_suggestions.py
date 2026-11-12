"""suggestions: AI prompt/poll suggestions awaiting admin approval

Revision ID: 0029_suggestions
Revises: 0028_plugin_pending_manifest
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision = "0029_suggestions"
down_revision = "0028_plugin_pending_manifest"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "suggestions",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "community_id",
            UUID(as_uuid=True),
            sa.ForeignKey("communities.id", ondelete="CASCADE"),
            nullable=False,
            server_default="00000000-0000-0000-0000-000000000001",
        ),
        sa.Column("type", sa.Text, nullable=False),
        sa.Column("content", JSONB, nullable=False),
        sa.Column("suggested_by", sa.Text, nullable=False, server_default="ai"),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column(
            "approved_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")
        ),
        sa.Column("rejected_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("type IN ('prompt', 'poll')", name="ck_suggestions_type"),
    )
    op.create_index(
        "idx_suggestions_community_type",
        "suggestions",
        ["community_id", "type"],
        postgresql_where=sa.text("approved_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("idx_suggestions_community_type", table_name="suggestions")
    op.drop_table("suggestions")
