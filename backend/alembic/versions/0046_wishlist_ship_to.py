"""wishlist shipping address: free text, a person's shared address, or an event

@file 0046_wishlist_ship_to.py
@brief ship_to_text / ship_to_user_id / ship_to_event_id on wishlists.

Revision ID: 0046_wishlist_ship_to
Revises: 0045_amazon_settings
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision = "0046_wishlist_ship_to"
down_revision = "0045_amazon_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("wishlists", sa.Column("ship_to_text", sa.Text(), nullable=True))
    op.add_column(
        "wishlists",
        sa.Column(
            "ship_to_user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "wishlists",
        sa.Column(
            "ship_to_event_id",
            UUID(as_uuid=True),
            sa.ForeignKey("events.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("wishlists", "ship_to_event_id")
    op.drop_column("wishlists", "ship_to_user_id")
    op.drop_column("wishlists", "ship_to_text")
