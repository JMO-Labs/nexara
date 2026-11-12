"""add_apprise_urls: encrypted per-user Apprise targets

Revision ID: b7c1d2e3f4a5
Revises: 0023_bookmarks
Create Date: 2026-11-12 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7c1d2e3f4a5"
down_revision: str | Sequence[str] | None = "0023_bookmarks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create apprise_urls table."""
    op.create_table(
        "apprise_urls",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "community_id",
            UUID(as_uuid=True),
            sa.ForeignKey("communities.id", ondelete="CASCADE"),
            nullable=False,
            server_default="00000000-0000-0000-0000-000000000001",
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("apprise_url", sa.Text(), nullable=False),
        sa.Column("label", sa.String(100), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("failure_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_failure_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("apprise_urls_user_idx", "apprise_urls", ["user_id"])


def downgrade() -> None:
    """Drop apprise_urls table."""
    op.drop_index("apprise_urls_user_idx", table_name="apprise_urls")
    op.drop_table("apprise_urls")
