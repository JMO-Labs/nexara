"""media_ai_metadata table for OCR text

Revision ID: 0019_media_ai_metadata
Revises: a78f91338679
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID

from alembic import op

revision = "0019_media_ai_metadata"
down_revision = "a78f91338679"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "media_ai_metadata",
        sa.Column(
            "media_id",
            UUID(as_uuid=True),
            sa.ForeignKey("media.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("ocr_text", sa.Text()),
        sa.Column(
            "ocr_fts",
            TSVECTOR(),
            sa.Computed("to_tsvector('english', ocr_text)", persisted=True),
        ),
        sa.Column("description", sa.Text()),
        sa.Column("tags", JSONB()),
        sa.Column("processed_at", sa.DateTime(timezone=True)),
        sa.Column(
            "community_id",
            UUID(as_uuid=True),
            sa.ForeignKey("communities.id"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "idx_media_ai_metadata_ocr_fts",
        "media_ai_metadata",
        ["ocr_fts"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("idx_media_ai_metadata_ocr_fts", table_name="media_ai_metadata")
    op.drop_table("media_ai_metadata")
