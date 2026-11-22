"""wishlists_v2: recipients, money, dates, registries, funds and link previews

- occasion presets widen (free-form ``occasion_label``); event_date + due_by
- currency, budget guidance, event budget, per-giver cap, hide_claims
- registry_links (Amazon and other registries)
- wishlist_recipients: members, household members, groups, names or everyone
  (replaces wishlists.household_id)
- items: gift|fund, price_cents / goal_cents, link preview; claims: amount_cents

Revision ID: 0042_wishlists_v2
Revises: 0041_wishlists
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision: str = "0042_wishlists_v2"
down_revision: str | Sequence[str] | None = "0041_wishlists"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

COMMUNITY = sa.text("'00000000-0000-0000-0000-000000000001'::uuid")


def upgrade() -> None:
    """@brief Widen wishlists; move household_id into recipients."""
    op.drop_constraint("wishlists_occasion_ck", "wishlists", type_="check")
    op.alter_column("wishlists", "occasion_date", new_column_name="event_date")
    for col in [
        sa.Column("occasion_label", sa.Text()),
        sa.Column("due_by", sa.Date()),
        sa.Column("currency", sa.Text(), nullable=False, server_default="USD"),
        sa.Column("budget_min_cents", sa.Integer()),
        sa.Column("budget_max_cents", sa.Integer()),
        sa.Column("event_budget_cents", sa.Integer()),
        sa.Column("giver_cap_cents", sa.Integer()),
        sa.Column("hide_claims", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("registry_links", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
    ]:
        op.add_column("wishlists", col)
    op.create_table(
        "wishlist_recipients",
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
            "wishlist_id",
            UUID(as_uuid=True),
            sa.ForeignKey("wishlists.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("ref_id", UUID(as_uuid=True)),
        sa.Column("name", sa.Text()),
        sa.CheckConstraint(
            "kind IN ('user','household','subgroup','name','everyone')",
            name="wishlist_recipients_kind_ck",
        ),
    )
    op.create_index("wishlist_recipients_list_idx", "wishlist_recipients", ["wishlist_id"])
    op.create_index("wishlist_recipients_ref_idx", "wishlist_recipients", ["kind", "ref_id"])
    op.execute(
        "INSERT INTO wishlist_recipients (community_id, wishlist_id, kind, ref_id) "
        "SELECT community_id, id, 'household', household_id FROM wishlists "
        "WHERE household_id IS NOT NULL"
    )
    op.drop_index("wishlists_household_idx", table_name="wishlists")
    op.drop_column("wishlists", "household_id")

    op.add_column(
        "wishlist_items", sa.Column("kind", sa.Text(), nullable=False, server_default="gift")
    )
    op.create_check_constraint(
        "wishlist_items_kind_ck", "wishlist_items", "kind IN ('gift','fund')"
    )
    op.add_column("wishlist_items", sa.Column("price_cents", sa.Integer()))
    op.add_column("wishlist_items", sa.Column("goal_cents", sa.Integer()))
    op.add_column(
        "wishlist_items",
        sa.Column(
            "preview_id",
            UUID(as_uuid=True),
            sa.ForeignKey("link_previews.id", ondelete="SET NULL"),
        ),
    )
    op.execute(
        "UPDATE wishlist_items SET price_cents = round(100 * "
        "substring(replace(price, ',', '') from '[0-9]+(\\.[0-9]+)?')::numeric) "
        "WHERE price ~ '[0-9]'"
    )
    op.drop_column("wishlist_items", "price")
    op.add_column("wishlist_claims", sa.Column("amount_cents", sa.Integer()))


def downgrade() -> None:
    """@brief Back to v1 (recipients other than one household member are lost)."""
    op.drop_column("wishlist_claims", "amount_cents")
    op.add_column("wishlist_items", sa.Column("price", sa.Text()))
    op.execute(
        "UPDATE wishlist_items SET price = to_char(price_cents / 100.0, 'FM999999990.00') "
        "WHERE price_cents IS NOT NULL"
    )
    for c in ("preview_id", "goal_cents", "price_cents"):
        op.drop_column("wishlist_items", c)
    op.drop_constraint("wishlist_items_kind_ck", "wishlist_items", type_="check")
    op.drop_column("wishlist_items", "kind")
    op.add_column(
        "wishlists",
        sa.Column(
            "household_id",
            UUID(as_uuid=True),
            sa.ForeignKey("household_members.id", ondelete="CASCADE"),
        ),
    )
    op.create_index("wishlists_household_idx", "wishlists", ["household_id"])
    op.execute(
        "UPDATE wishlists w SET household_id = r.ref_id FROM wishlist_recipients r "
        "WHERE r.wishlist_id = w.id AND r.kind = 'household'"
    )
    op.drop_table("wishlist_recipients")
    for c in (
        "registry_links",
        "hide_claims",
        "giver_cap_cents",
        "event_budget_cents",
        "budget_max_cents",
        "budget_min_cents",
        "currency",
        "due_by",
        "occasion_label",
    ):
        op.drop_column("wishlists", c)
    op.alter_column("wishlists", "event_date", new_column_name="occasion_date")
    op.execute(
        "UPDATE wishlists SET occasion = 'custom' WHERE occasion NOT IN "
        "('birthday','holiday','school','wedding','baby','custom')"
    )
    op.create_check_constraint(
        "wishlists_occasion_ck",
        "wishlists",
        "occasion IN ('birthday','holiday','school','wedding','baby','custom')",
    )
