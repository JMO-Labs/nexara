"""
@file 0067_prompt_answer_recount.py
@brief Recompute prompt_posts.response_count from live answers. Deleted
       answers used to leave the counter too high.

Revision ID: 0067_prompt_answer_recount
Revises: 0066_reply_email
"""

from __future__ import annotations

from alembic import op

revision = "0067_prompt_answer_recount"
down_revision = "0066_reply_email"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """@brief Set every counter to the number of non-deleted answers."""
    op.execute(
        """
        UPDATE prompt_posts pp
        SET response_count = (
            SELECT count(*) FROM posts p
            WHERE p.reply_to_prompt_id = pp.id AND p.deleted_at IS NULL
        )
        """
    )


def downgrade() -> None:
    """@brief Data-only fix; nothing to undo."""
