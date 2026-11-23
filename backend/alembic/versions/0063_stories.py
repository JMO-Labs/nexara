"""Voice stories: story requests.

@file 0063_stories.py
@brief Create story_requests and add posts.story_request_id.

Revision ID: 0063_stories
Revises: 0059_chore_rotation
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0063_stories"
# ponytail: chained to 0059 in this worktree; orchestrator re-chains at merge.
down_revision = "0059_chore_rotation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """@brief Create story_requests, then link posts to it."""
    op.create_table(
        "story_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("community_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("communities.id", ondelete="CASCADE"), nullable=False, server_default=sa.text("'00000000-0000-0000-0000-000000000001'::uuid")),
        sa.Column("asker_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("teller_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="open"),
        sa.Column("post_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("posts.id", ondelete="SET NULL")),
        sa.Column("reminded_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now() + interval '30 days'")),
        sa.CheckConstraint("status IN ('open','answered','declined','expired')", name="story_requests_status_ck"),
        sa.CheckConstraint("char_length(question) <= 280", name="story_requests_question_ck"),
    )  # fmt: skip
    op.create_index("story_requests_teller_idx", "story_requests", ["teller_id", "status"])
    op.create_index("story_requests_asker_idx", "story_requests", ["asker_id", "teller_id"])
    op.add_column(
        "posts",
        sa.Column(
            "story_request_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("story_requests.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "posts_story_request_idx",
        "posts",
        ["story_request_id"],
        postgresql_where=sa.text("story_request_id IS NOT NULL"),
    )


def downgrade() -> None:
    """@brief Drop the post link, then the table."""
    op.drop_index("posts_story_request_idx", table_name="posts")
    op.drop_column("posts", "story_request_id")
    op.drop_index("story_requests_asker_idx", table_name="story_requests")
    op.drop_index("story_requests_teller_idx", table_name="story_requests")
    op.drop_table("story_requests")
