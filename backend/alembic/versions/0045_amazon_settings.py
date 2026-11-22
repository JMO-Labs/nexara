"""amazon creators api settings on community

@file 0045_amazon_settings.py
@brief Admin-managed Amazon credentials (secret stored encrypted).

Revision ID: 0045_amazon_settings
Revises: 0044_shop_prices
"""

import sqlalchemy as sa

from alembic import op

revision = "0045_amazon_settings"
down_revision = "0044_shop_prices"
branch_labels = None
depends_on = None

COLS = ("amazon_client_id", "amazon_client_secret", "amazon_partner_tag", "amazon_marketplace")


def upgrade() -> None:
    for c in COLS:
        op.add_column("communities", sa.Column(c, sa.Text(), nullable=True))


def downgrade() -> None:
    for c in COLS:
        op.drop_column("communities", c)
