"""add FTS columns and branding unique constraint

Revision ID: 0002
Revises: 0001
Create Date: 2026-02-26 18:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- Users: search_fts (display_name + username + bio) ---
    op.execute(
        "ALTER TABLE users ADD COLUMN search_fts TSVECTOR "
        "GENERATED ALWAYS AS ("
        "to_tsvector('english', "
        "coalesce(display_name, '') || ' ' || "
        "coalesce(username, '') || ' ' || "
        "coalesce(bio, ''))"
        ") STORED;"
    )
    op.execute("CREATE INDEX users_search_fts_idx ON users USING GIN (search_fts);")

    # --- Events: search_fts (title + description + location) ---
    op.execute(
        "ALTER TABLE events ADD COLUMN search_fts TSVECTOR "
        "GENERATED ALWAYS AS ("
        "to_tsvector('english', "
        "coalesce(title, '') || ' ' || "
        "coalesce(description, '') || ' ' || "
        "coalesce(location, ''))"
        ") STORED;"
    )
    op.execute("CREATE INDEX events_search_fts_idx ON events USING GIN (search_fts);")

    # --- Galleries: search_fts (title + description) ---
    op.execute(
        "ALTER TABLE galleries ADD COLUMN search_fts TSVECTOR "
        "GENERATED ALWAYS AS ("
        "to_tsvector('english', "
        "coalesce(title, '') || ' ' || "
        "coalesce(description, ''))"
        ") STORED;"
    )
    op.execute("CREATE INDEX galleries_search_fts_idx ON galleries USING GIN (search_fts);")

    # --- Subgroups: search_fts (name + description) ---
    op.execute(
        "ALTER TABLE subgroups ADD COLUMN search_fts TSVECTOR "
        "GENERATED ALWAYS AS ("
        "to_tsvector('english', "
        "coalesce(name, '') || ' ' || "
        "coalesce(description, ''))"
        ") STORED;"
    )
    op.execute("CREATE INDEX subgroups_search_fts_idx ON subgroups USING GIN (search_fts);")

    # --- Unique constraint on community_branding.community_id ---
    op.create_unique_constraint(
        "uq_community_branding_community_id",
        "community_branding",
        ["community_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_community_branding_community_id",
        "community_branding",
        type_="unique",
    )

    op.execute("DROP INDEX IF EXISTS subgroups_search_fts_idx;")
    op.execute("ALTER TABLE subgroups DROP COLUMN IF EXISTS search_fts;")

    op.execute("DROP INDEX IF EXISTS galleries_search_fts_idx;")
    op.execute("ALTER TABLE galleries DROP COLUMN IF EXISTS search_fts;")

    op.execute("DROP INDEX IF EXISTS events_search_fts_idx;")
    op.execute("ALTER TABLE events DROP COLUMN IF EXISTS search_fts;")

    op.execute("DROP INDEX IF EXISTS users_search_fts_idx;")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS search_fts;")
