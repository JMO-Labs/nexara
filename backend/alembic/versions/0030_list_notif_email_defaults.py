"""list.expiring and list.member email notifications default on

Revision ID: 0030_list_notif_email_defaults
Revises: b2c3d4e5f6a7
"""

import sqlalchemy as sa

from alembic import op

revision = "0030_list_notif_email_defaults"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None

_COLS = ("notif_list_expiring_email", "notif_list_member_email")


def upgrade() -> None:
    for col in _COLS:
        op.alter_column("user_settings", col, server_default=sa.text("true"))


def downgrade() -> None:
    for col in _COLS:
        op.alter_column("user_settings", col, server_default=sa.text("false"))
