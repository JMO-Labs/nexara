"""perf indexes: attendance user lookup, notification unread feed, post media join

Revision ID: 0034_perf_indexes
Revises: 0033_branding_glass_defaults
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0034_perf_indexes"
down_revision: str | Sequence[str] | None = "0033_branding_glass_defaults"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """@brief Add attendance/post_media indexes and replace the notification unread index."""
    op.execute("CREATE INDEX IF NOT EXISTS attendance_user_idx ON event_attendance (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS post_media_media_idx ON post_media (media_id)")
    op.execute("DROP INDEX IF EXISTS notifications_user_unread_idx")
    op.execute(
        "CREATE INDEX notifications_user_unread_idx ON notifications "
        "(user_id, created_at DESC) WHERE read_at IS NULL AND dismissed_at IS NULL"
    )


def downgrade() -> None:
    """@brief Reverse upgrade: restore the original unread index and drop new indexes."""
    op.execute("DROP INDEX IF EXISTS notifications_user_unread_idx")
    op.execute(
        "CREATE INDEX notifications_user_unread_idx ON notifications "
        "(user_id, read_at) WHERE read_at IS NULL"
    )
    op.execute("DROP INDEX IF EXISTS post_media_media_idx")
    op.execute("DROP INDEX IF EXISTS attendance_user_idx")
