"""wishlists: gift lists with items and claims hidden from the owner

Revision ID: 0041_wishlists
Revises: 0040_aegean_branding_defaults
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "0041_wishlists"
down_revision: str | Sequence[str] | None = "0040_aegean_branding_defaults"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

COMMUNITY = sa.text("'00000000-0000-0000-0000-000000000001'::uuid")


def _base() -> list[sa.Column]:  # type: ignore[type-arg]
    return [
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "community_id",
            UUID(as_uuid=True),
            sa.ForeignKey("communities.id", ondelete="CASCADE"),
            nullable=False,
            server_default=COMMUNITY,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    ]


def upgrade() -> None:
    """@brief wishlists, wishlist_items, wishlist_claims."""
    op.create_table(
        "wishlists",
        *_base(),
        sa.Column(
            "owner_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "household_id",
            UUID(as_uuid=True),
            sa.ForeignKey("household_members.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("occasion", sa.Text(), nullable=False, server_default="custom"),
        sa.Column("occasion_date", sa.Date(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("visibility", sa.Text(), nullable=False, server_default="groups"),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "occasion IN ('birthday','holiday','school','wedding','baby','custom')",
            name="wishlists_occasion_ck",
        ),
        sa.CheckConstraint(
            "visibility IN ('private','groups','community')", name="wishlists_visibility_ck"
        ),
    )
    op.create_index("wishlists_owner_idx", "wishlists", ["owner_id"])
    op.create_index("wishlists_household_idx", "wishlists", ["household_id"])
    op.create_table(
        "wishlist_items",
        *_base(),
        sa.Column(
            "wishlist_id",
            UUID(as_uuid=True),
            sa.ForeignKey("wishlists.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("price", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("qty", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("qty BETWEEN 1 AND 99", name="wishlist_items_qty_ck"),
    )
    op.create_index("wishlist_items_list_idx", "wishlist_items", ["wishlist_id"])
    op.create_table(
        "wishlist_claims",
        *_base(),
        sa.Column(
            "item_id",
            UUID(as_uuid=True),
            sa.ForeignKey("wishlist_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("qty", sa.Integer(), nullable=False, server_default="1"),
        sa.UniqueConstraint("item_id", "user_id", name="wishlist_claims_unique"),
        sa.CheckConstraint("qty >= 1", name="wishlist_claims_qty_ck"),
    )


def downgrade() -> None:
    """@brief Drop the wishlist tables."""
    op.drop_table("wishlist_claims")
    op.drop_table("wishlist_items")
    op.drop_table("wishlists")
