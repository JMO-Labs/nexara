"""add FTS column and GIN index to comments table

Revision ID: 0003
Revises: 0002
Create Date: 2026-02-28 12:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE comments ADD COLUMN content_fts TSVECTOR "
        "GENERATED ALWAYS AS ("
        "to_tsvector('english', content)"
        ") STORED"
    )
    op.create_index(
        "comments_fts_idx",
        "comments",
        ["content_fts"],
        unique=False,
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("comments_fts_idx", table_name="comments")
    op.drop_column("comments", "content_fts")
