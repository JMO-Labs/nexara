"""add chat_messages.channel_id and direct_message_participants

Revision ID: 0006
Revises: 0005
Create Date: 2026-04-18 12:00:00.000000

Introduces chat infrastructure for Phase 2 Group 2:
  * Adds ``channel_id`` foreign key on ``chat_messages`` so each message
    is linked to a :class:`ChatChannel` (community, subgroup, or direct).
  * Adds a composite index on ``(channel_id, created_at DESC)`` to make
    history-by-channel queries efficient.
  * Creates the ``direct_message_participants`` join table so a pair of
    users can be associated with a DM-type channel and looked up via a
    canonical sorted-pair query.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """@brief Add channel_id + index and create direct_message_participants."""
    op.add_column(
        "chat_messages",
        sa.Column("channel_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "chat_messages_channel_id_fkey",
        "chat_messages",
        "chat_channels",
        ["channel_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "chat_messages_channel_idx",
        "chat_messages",
        ["channel_id", sa.literal_column("created_at DESC")],
        unique=False,
    )

    op.create_table(
        "direct_message_participants",
        sa.Column("channel_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["channel_id"], ["chat_channels.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("channel_id", "user_id"),
    )
    op.create_index(
        "dm_participants_user_idx",
        "direct_message_participants",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    """@brief Reverse the chat schema changes."""
    op.drop_index("dm_participants_user_idx", table_name="direct_message_participants")
    op.drop_table("direct_message_participants")
    op.drop_index("chat_messages_channel_idx", table_name="chat_messages")
    op.drop_constraint("chat_messages_channel_id_fkey", "chat_messages", type_="foreignkey")
    op.drop_column("chat_messages", "channel_id")
