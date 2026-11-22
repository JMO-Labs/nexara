"""Extend tags to support lists, events, and chat messages.

@file 0049_tag_targets.py
@brief Widen tags_target_type_ck constraint to include list, event, chat_message.

Revision ID: 0049_tag_targets
Revises: 0048_celebrate_posts
"""

from alembic import op

revision = "0049_tag_targets"
down_revision = "0048_celebrate_posts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """@brief Extend tags_target_type_ck to include list, event, chat_message."""
    op.drop_constraint("tags_target_type_ck", "tags", type_="check")
    op.create_check_constraint(
        "tags_target_type_ck",
        "tags",
        "target_type IN ('post','comment','media','list','event','chat_message')",
    )


def downgrade() -> None:
    """@brief Revert tags_target_type_ck to original constraint."""
    op.execute("DELETE FROM tags WHERE target_type IN ('list','event','chat_message')")
    op.drop_constraint("tags_target_type_ck", "tags", type_="check")
    op.create_check_constraint(
        "tags_target_type_ck",
        "tags",
        "target_type IN ('post','comment','media')",
    )
