"""rename pronouns to title in users table

Revision ID: 0004
Revises: 0003
Create Date: 2026-02-28 14:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "users",
        "pronouns",
        new_column_name="title",
    )


def downgrade() -> None:
    op.alter_column(
        "users",
        "title",
        new_column_name="pronouns",
    )
