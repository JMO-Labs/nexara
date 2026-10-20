"""add magic_link_tokens table and poll visibility columns

Revision ID: 0005
Revises: 32ad668e259b
Create Date: 2026-03-03 20:00:00.000000

Adds the magic_link_tokens table for passwordless login and
result_visibility / closed columns to polls.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: str | None = "32ad668e259b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "magic_link_tokens",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("magic_link_tokens_user_idx", "magic_link_tokens", ["user_id"])
    op.create_index("magic_link_tokens_hash_idx", "magic_link_tokens", ["token_hash"])

    op.add_column(
        "polls",
        sa.Column(
            "result_visibility",
            sa.String(length=16),
            server_default="after_vote",
            nullable=False,
        ),
    )
    op.add_column(
        "polls",
        sa.Column(
            "closed",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("polls", "closed")
    op.drop_column("polls", "result_visibility")
    op.drop_index("magic_link_tokens_hash_idx", table_name="magic_link_tokens")
    op.drop_index("magic_link_tokens_user_idx", table_name="magic_link_tokens")
    op.drop_table("magic_link_tokens")
