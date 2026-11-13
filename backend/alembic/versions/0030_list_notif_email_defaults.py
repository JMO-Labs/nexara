"""list.expiring and list.member email notifications default on

Also merges the two dev heads (apprise_urls, list_notified_at).
Only server_default changes: existing rows keep their current values.

Revision ID: 0030_list_notif_email_defaults
Revises: b7c1d2e3f4a5, e5f6a7b8c9d0 (merge revision)
"""

import sqlalchemy as sa

from alembic import op

revision = "0030_list_notif_email_defaults"
down_revision = ("b7c1d2e3f4a5", "e5f6a7b8c9d0")
branch_labels = None
depends_on = None

_COLS = ("notif_list_expiring_email", "notif_list_member_email")


def upgrade() -> None:
    for col in _COLS:
        op.alter_column("user_settings", col, server_default=sa.text("true"))


def downgrade() -> None:
    for col in _COLS:
        op.alter_column("user_settings", col, server_default=sa.text("false"))
