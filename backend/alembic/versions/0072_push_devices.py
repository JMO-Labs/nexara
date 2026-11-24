"""Push devices: name and last_used_at on push_subscriptions.

@file 0072_push_devices.py
@brief Adds push_subscriptions.name and last_used_at for per-device management.

Revision ID: 0072_push_devices
Revises: 0071_sso_sync
"""

import sqlalchemy as sa

from alembic import op

revision = "0072_push_devices"
down_revision = "0071_sso_sync"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """@brief Add nullable name and last_used_at."""
    op.add_column("push_subscriptions", sa.Column("name", sa.Text(), nullable=True))
    op.add_column(
        "push_subscriptions", sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    """@brief Drop the added columns."""
    op.drop_column("push_subscriptions", "last_used_at")
    op.drop_column("push_subscriptions", "name")
