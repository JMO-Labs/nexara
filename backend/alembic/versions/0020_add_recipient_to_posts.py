"""add recipient_id to posts (kudos)

Revision ID: 0020_add_recipient_to_posts
Revises: 0019_add_oidc_provider_fields
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0020_add_recipient_to_posts"
down_revision: str | None = "0019_add_oidc_provider_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "posts",
        sa.Column(
            "recipient_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "posts_recipient_idx",
        "posts",
        ["recipient_id"],
        postgresql_where=sa.text("recipient_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("posts_recipient_idx", table_name="posts")
    op.drop_column("posts", "recipient_id")
