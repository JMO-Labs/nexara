"""subgroup: add cover_media_id foreign key

Revision ID: 0018_subgroup_cover_media
Revises: 0017_event_locally_modified
"""
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision = "0018_subgroup_cover_media"
down_revision = "0017_event_locally_modified"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "subgroups",
        sa.Column(
            "cover_media_id",
            UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_subgroups_cover_media_id",
        "subgroups",
        ["cover_media_id"],
    )
    op.create_foreign_key(
        "fk_subgroups_cover_media_id",
        "subgroups",
        "media",
        ["cover_media_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_subgroups_cover_media_id", "subgroups", type_="foreignkey")
    op.drop_index("ix_subgroups_cover_media_id", table_name="subgroups")
    op.drop_column("subgroups", "cover_media_id")
