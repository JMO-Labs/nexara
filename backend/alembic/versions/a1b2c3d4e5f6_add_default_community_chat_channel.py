"""add default community chat channel

@file a1b2c3d4e5f6_add_default_community_chat_channel.py
@brief Backfill: ensure every existing community has a default community-root
       General chat channel (channel_type='community', subgroup_id=NULL).

NOTE: This migration is chained onto a4b2e1f9c8d0 (activity_event). If those
two phases land separately the down_revision below may need adjusting.

Revision ID: a1b2c3d4e5f6
Revises: a4b2e1f9c8d0
Create Date: 2026-04-30
"""

from collections.abc import Sequence

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "a4b2e1f9c8d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Insert a default 'General' community-level chat channel per community.

    Idempotent: only inserts when no community-level channel exists for the
    community.
    """
    op.execute(
        """
        INSERT INTO chat_channels (community_id, name, channel_type, subgroup_id)
        SELECT c.id, 'General', 'community', NULL
        FROM communities c
        WHERE NOT EXISTS (
            SELECT 1
            FROM chat_channels ch
            WHERE ch.community_id = c.id
              AND ch.channel_type = 'community'
              AND ch.subgroup_id IS NULL
        )
        """
    )


def downgrade() -> None:
    """Remove default General community-level chat channels."""
    op.execute(
        """
        DELETE FROM chat_channels
        WHERE channel_type = 'community'
          AND subgroup_id IS NULL
          AND name = 'General'
        """
    )
