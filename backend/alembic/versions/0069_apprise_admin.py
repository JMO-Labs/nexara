"""Apprise admin targets and local-network opt-in.

@file 0069_apprise_admin.py
@brief apprise_urls.user_id nullable + is_admin_target; communities.apprise_allow_local.

Revision ID: 0069_apprise_admin
Revises: 0068_mail_signin
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision = "0069_apprise_admin"
down_revision = "0068_mail_signin"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("apprise_urls", "user_id", existing_type=UUID(as_uuid=True), nullable=True)
    op.add_column(
        "apprise_urls",
        sa.Column("is_admin_target", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "communities",
        sa.Column("apprise_allow_local", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("communities", "apprise_allow_local")
    op.execute("DELETE FROM apprise_urls WHERE user_id IS NULL")
    op.drop_column("apprise_urls", "is_admin_target")
    op.alter_column("apprise_urls", "user_id", existing_type=UUID(as_uuid=True), nullable=False)
