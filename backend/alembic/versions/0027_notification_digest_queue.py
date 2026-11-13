"""add notification_digest_queue table

Revision ID: 0027_notification_digest_queue
Revises: 0026_user_exports_table
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0027_notification_digest_queue"
down_revision: str | None = "0026_user_exports_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notification_digest_queue",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.func.gen_random_uuid(),
        ),
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
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index(
        "ix_digest_queue_user_type", "notification_digest_queue", ["user_id", "type_key"]
    )


def downgrade() -> None:
    op.drop_index("ix_digest_queue_user_type", table_name="notification_digest_queue")
    op.drop_table("notification_digest_queue")
