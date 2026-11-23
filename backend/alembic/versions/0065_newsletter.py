"""Printable newsletter: admin pin/hide overrides.

@file 0065_newsletter.py
@brief Create newsletter_overrides.

Revision ID: 0065_newsletter
Revises: 0063_stories
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0065_newsletter"
# ponytail: chained to 0063 in this worktree; orchestrator re-chains at merge.
down_revision = "0063_stories"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """@brief Create newsletter_overrides."""
    op.create_table(
        "newsletter_overrides",
        sa.Column("community_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("communities.id", ondelete="CASCADE"), nullable=False, server_default=sa.text("'00000000-0000-0000-0000-000000000001'::uuid")),
        sa.Column("month", sa.Text(), nullable=False),
        sa.Column("post_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("posts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("community_id", "month", "post_id"),
        sa.CheckConstraint("action IN ('pin','hide')", name="newsletter_overrides_action_ck"),
        sa.CheckConstraint("month ~ '^[0-9]{4}-[0-9]{2}$'", name="newsletter_overrides_month_ck"),
    )  # fmt: skip


def downgrade() -> None:
    """@brief Drop newsletter_overrides."""
    op.drop_table("newsletter_overrides")
