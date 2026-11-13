"""merge apprise_urls and list_notified_at heads

Revision ID: 0030_merge_heads
Revises: b7c1d2e3f4a5, e5f6a7b8c9d0
"""

from collections.abc import Sequence

revision: str = "0030_merge_heads"
down_revision: str | Sequence[str] | None = ("b7c1d2e3f4a5", "e5f6a7b8c9d0")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """@brief No-op merge."""


def downgrade() -> None:
    """@brief No-op merge."""
