"""shop_prices: product price/currency/buy link on previews; auto prices on wishes

Revision ID: 0044_shop_prices
Revises: 0043_list_assignments
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0044_shop_prices"
down_revision: str | Sequence[str] | None = "0043_list_assignments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """@brief Shop facts on link previews; flag prices that follow the shop."""
    op.add_column("link_previews", sa.Column("price_cents", sa.Integer()))
    op.add_column("link_previews", sa.Column("currency", sa.Text()))
    op.add_column("link_previews", sa.Column("buy_url", sa.Text()))
    op.add_column(
        "wishlist_items",
        sa.Column("price_auto", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    """@brief Drop the shop columns."""
    op.drop_column("wishlist_items", "price_auto")
    for c in ("buy_url", "currency", "price_cents"):
        op.drop_column("link_previews", c)
