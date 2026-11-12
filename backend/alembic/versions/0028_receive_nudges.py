"""add receive_nudges opt-out to user_settings (nexara#62)

Revision ID: 0028_receive_nudges
Revises: b2c3d4e5f6a7
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0028_receive_nudges"
down_revision: str | Sequence[str] | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user_settings",
        sa.Column("receive_nudges", sa.Boolean(), nullable=False, server_default="true"),
    )


def downgrade() -> None:
    op.drop_column("user_settings", "receive_nudges")
