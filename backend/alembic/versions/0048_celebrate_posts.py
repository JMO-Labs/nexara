"""celebrate posts: a post celebrating a person or pet's occasion

@file 0048_celebrate_posts.py
@brief posts.celebrate_type ('user'|'household'), celebrate_id, celebrate_occasion.

Revision ID: 0048_celebrate_posts
Revises: 0047_household_handle
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision = "0048_celebrate_posts"
down_revision = "0047_household_handle"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("posts", sa.Column("celebrate_type", sa.Text(), nullable=True))
    op.add_column("posts", sa.Column("celebrate_id", UUID(as_uuid=True), nullable=True))
    op.add_column("posts", sa.Column("celebrate_occasion", sa.Text(), nullable=True))
    op.create_check_constraint(
        "posts_celebrate_ck",
        "posts",
        "(celebrate_type IS NULL AND celebrate_id IS NULL AND celebrate_occasion IS NULL)"
        " OR (celebrate_type IN ('user','household') AND celebrate_id IS NOT NULL"
        " AND celebrate_occasion IN ('birthday','gotcha_day','milestone'))",
    )


def downgrade() -> None:
    op.drop_constraint("posts_celebrate_ck", "posts")
    for c in ("celebrate_occasion", "celebrate_id", "celebrate_type"):
        op.drop_column("posts", c)
