"""household member @handles for mentions

@file 0047_household_handle.py
@brief handle column (unique per community among live members), backfilled
       from names, avoiding usernames and group slugs.

Revision ID: 0047_household_handle
Revises: 0046_wishlist_ship_to
"""

import re

import sqlalchemy as sa

from alembic import op

revision = "0047_household_handle"
down_revision = "0046_wishlist_ship_to"
branch_labels = None
depends_on = None


def _slug(name: str, kind: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:30].strip("-")
    return s or ("pet" if kind == "pet" else "family")


def upgrade() -> None:
    op.add_column("household_members", sa.Column("handle", sa.Text(), nullable=True))
    bind = op.get_bind()
    taken: dict[str, set[str]] = {}
    for cid, name in bind.execute(sa.text("SELECT community_id, lower(username) FROM users")):
        taken.setdefault(str(cid), set()).add(name)
    slugs = {r[0] for r in bind.execute(sa.text("SELECT lower(slug) FROM subgroups"))}
    rows = bind.execute(
        sa.text(
            "SELECT id, community_id, name, kind FROM household_members "
            "WHERE deleted_at IS NULL ORDER BY created_at"
        )
    ).all()
    for mid, cid, name, kind in rows:
        used = taken.setdefault(str(cid), set())
        base, n, cand = _slug(name, kind), 1, _slug(name, kind)
        while cand in used or cand in slugs:
            n += 1
            cand = f"{base[: 30 - len(str(n)) - 1]}-{n}"
        used.add(cand)
        bind.execute(
            sa.text("UPDATE household_members SET handle = :h WHERE id = :id"),
            {"h": cand, "id": mid},
        )
    op.create_index(
        "household_members_handle_uq",
        "household_members",
        ["community_id", "handle"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL AND handle IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("household_members_handle_uq", table_name="household_members")
    op.drop_column("household_members", "handle")
