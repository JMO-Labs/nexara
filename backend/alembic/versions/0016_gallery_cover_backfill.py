"""gallery: backfill cover_media_id from first item

Revision ID: 0016_gallery_cover_backfill
Revises: 0015_event_original_start
"""

from alembic import op

revision = "0016_gallery_cover_backfill"
down_revision = "0015_event_original_start"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE galleries g
        SET cover_media_id = sub.media_id
        FROM (
            SELECT DISTINCT ON (gallery_id) gallery_id, media_id
            FROM gallery_items
            ORDER BY gallery_id, position ASC, created_at ASC
        ) AS sub
        WHERE g.id = sub.gallery_id
          AND g.cover_media_id IS NULL
        """
    )


def downgrade() -> None:
    pass
