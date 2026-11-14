"""apprise per-type prefs: backfill apprise=false.

No new columns: notification_prefs JSONB already exists. Every type entry
gets ``apprise: false`` (opt-in).

Revision ID: c5d6e7f8a9b0
Revises: 0031_receive_nudges
Create Date: 2026-11-13
"""

from collections.abc import Sequence

from alembic import op

revision: str = "c5d6e7f8a9b0"
down_revision: str | Sequence[str] | None = "0031_receive_nudges"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """@brief Add apprise:false to each type entry lacking it (keeps user values)."""
    op.execute(
        """
        UPDATE user_settings SET notification_prefs = COALESCE((
            SELECT jsonb_object_agg(
                k, CASE WHEN jsonb_typeof(v) = 'object'
                        THEN jsonb_build_object('apprise', false) || v ELSE v END)
            FROM jsonb_each(notification_prefs) AS t(k, v)
        ), notification_prefs)
        """
    )


def downgrade() -> None:
    """@brief Remove the apprise key from every type entry."""
    op.execute(
        """
        UPDATE user_settings SET notification_prefs = COALESCE((
            SELECT jsonb_object_agg(
                k, CASE WHEN jsonb_typeof(v) = 'object' THEN v - 'apprise' ELSE v END)
            FROM jsonb_each(notification_prefs) AS t(k, v)
        ), notification_prefs)
        """
    )
