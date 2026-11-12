"""add receive_nudges opt-out to user_settings (nexara#62)

Revision ID: 0026_receive_nudges
Revises: 0025_plugin_api_keys
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0026_receive_nudges"
down_revision: str | Sequence[str] | None = "0025_plugin_api_keys"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user_settings",
        sa.Column("receive_nudges", sa.Boolean(), nullable=False, server_default="true"),
    )


def downgrade() -> None:
    op.drop_column("user_settings", "receive_nudges")
