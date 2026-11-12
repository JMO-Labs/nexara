"""garden club default accent

Revision ID: a78f91338679
Revises: 9db194555fd0
Create Date: 2026-10-20 10:46:13.997278

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a78f91338679"
down_revision: str | None = "9db194555fd0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """@brief Old default accent failed AA against forest; move default rows to Garden Club lilac."""
    op.alter_column("community_branding", "color_accent", server_default="#C6B4F5")
    op.execute(
        "UPDATE community_branding SET color_accent = '#C6B4F5' "
        "WHERE lower(color_accent) = '#8b5cf6'"
    )


def downgrade() -> None:
    """@brief Restore old server default (rows are left as-is)."""
    op.alter_column("community_branding", "color_accent", server_default="#8b5cf6")
