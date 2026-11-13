"""list.expiring and list.member email notifications default on

Revision ID: 0030_list_notif_email_defaults
Revises: 0026_user_exports_table
"""

import sqlalchemy as sa

from alembic import op

revision = "0030_list_notif_email_defaults"
down_revision = "0026_user_exports_table"
branch_labels = None
depends_on = None

_COLS = ("notif_list_expiring_email", "notif_list_member_email")


def upgrade() -> None:
    for col in _COLS:
        op.alter_column("user_settings", col, server_default=sa.text("true"))


def downgrade() -> None:
    for col in _COLS:
        op.alter_column("user_settings", col, server_default=sa.text("false"))
