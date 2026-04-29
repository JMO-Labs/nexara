"""add_home_layout_to_user_settings

Revision ID: 9f8ff6e495e4
Revises: 0018_subgroup_cover_media
Create Date: 2026-04-29 10:29:19.513308

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = '9f8ff6e495e4'
down_revision: Union[str, None] = '0018_subgroup_cover_media'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_settings",
        sa.Column("home_layout", JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user_settings", "home_layout")
