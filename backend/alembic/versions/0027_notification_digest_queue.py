"""add notification_digest_queue table

Revision ID: 0027_notification_digest_queue
Revises: b7c1d2e3f4a5, e5f6a7b8c9d0 (merge point)
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0027_notification_digest_queue"
down_revision: tuple[str, ...] | None = ("b7c1d2e3f4a5", "e5f6a7b8c9d0")
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notification_digest_queue",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type_key", sa.Text(), nullable=False),
        sa.Column(
            "notification_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("notifications.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "enqueued_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("user_id", "notification_id"),
    )
    op.create_index(
        "digest_queue_drain_idx",
        "notification_digest_queue",
        ["user_id", "type_key", "enqueued_at"],
    )


def downgrade() -> None:
    op.drop_index("digest_queue_drain_idx", table_name="notification_digest_queue")
    op.drop_table("notification_digest_queue")
