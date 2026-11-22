"""Feature flags, community currency, user timezone.

@file 0050_features_tz.py
@brief Add communities.features/currency and users.timezone; seed timezone
       from user_settings.dnd_timezone.

Revision ID: 0050_features_tz
Revises: 0049_tag_targets
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0050_features_tz"
down_revision = "0049_tag_targets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """@brief Add columns and copy non-UTC DND timezones to users.timezone."""
    op.add_column(
        "communities",
        sa.Column(
            "features",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "communities",
        sa.Column("currency", sa.Text(), nullable=False, server_default="USD"),
    )
    op.create_check_constraint("communities_currency_ck", "communities", "currency ~ '^[A-Z]{3}$'")
    op.add_column("users", sa.Column("timezone", sa.Text(), nullable=True))
    op.execute(
        "UPDATE users u SET timezone = s.dnd_timezone FROM user_settings s "
        "WHERE s.user_id = u.id AND s.dnd_timezone IS NOT NULL AND s.dnd_timezone <> 'UTC'"
    )


def downgrade() -> None:
    """@brief Drop the added columns."""
    op.drop_column("users", "timezone")
    op.drop_constraint("communities_currency_ck", "communities", type_="check")
    op.drop_column("communities", "currency")
    op.drop_column("communities", "features")
