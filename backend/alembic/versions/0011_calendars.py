"""
@file 0011_calendars.py
@brief Introduce the Calendar entity and event.calendar_id FK.

Creates ``calendars`` table (kinds: personal, community, subgroup),
seeds one community calendar per community, one subgroup calendar per
subgroup, and one personal calendar per user. Backfills
``events.calendar_id`` from existing ``visibility`` + ``subgroup_id``
+ ``author_id``.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "calendars",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "community_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("communities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column(
            "owner_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "subgroup_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("subgroups.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("color", sa.Text(), nullable=True),
        sa.Column("external_provider", sa.Text(), nullable=True),
        sa.Column("external_id", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "kind IN ('personal', 'community', 'subgroup')",
            name="calendars_kind_check",
        ),
        sa.CheckConstraint(
            "(kind = 'personal' AND owner_id IS NOT NULL AND subgroup_id IS NULL) OR "
            "(kind = 'subgroup' AND subgroup_id IS NOT NULL AND owner_id IS NULL) OR "
            "(kind = 'community' AND owner_id IS NULL AND subgroup_id IS NULL)",
            name="calendars_kind_fk_check",
        ),
    )
    op.create_index(
        "calendars_one_personal_per_user",
        "calendars",
        ["community_id", "owner_id"],
        unique=True,
        postgresql_where=sa.text("owner_id IS NOT NULL"),
    )
    op.create_index(
        "calendars_one_per_subgroup",
        "calendars",
        ["community_id", "subgroup_id"],
        unique=True,
        postgresql_where=sa.text("subgroup_id IS NOT NULL"),
    )
    op.create_index(
        "calendars_one_community_per_community",
        "calendars",
        ["community_id"],
        unique=True,
        postgresql_where=sa.text("kind = 'community' AND deleted_at IS NULL"),
    )
    op.create_index("calendars_owner_idx", "calendars", ["owner_id"])
    op.create_index("calendars_subgroup_idx", "calendars", ["subgroup_id"])
    op.create_index("calendars_community_kind_idx", "calendars", ["community_id", "kind"])

    op.add_column(
        "events",
        sa.Column(
            "calendar_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("calendars.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("events_calendar_idx", "events", ["calendar_id"])

    # ── Seed calendars ───────────────────────────────────────────────
    # 1 community calendar per community
    op.execute(
        """
        INSERT INTO calendars (community_id, kind, name)
        SELECT id, 'community', 'Community'
        FROM communities
        ON CONFLICT DO NOTHING
        """
    )
    # 1 subgroup calendar per subgroup
    op.execute(
        """
        INSERT INTO calendars (community_id, kind, subgroup_id, name)
        SELECT community_id, 'subgroup', id, name
        FROM subgroups
        ON CONFLICT DO NOTHING
        """
    )
    # 1 personal calendar per user
    op.execute(
        """
        INSERT INTO calendars (community_id, kind, owner_id, name)
        SELECT community_id, 'personal', id, 'Personal'
        FROM users
        ON CONFLICT DO NOTHING
        """
    )

    # ── Backfill events.calendar_id ──────────────────────────────────
    op.execute(
        """
        UPDATE events e
        SET calendar_id = c.id
        FROM calendars c
        WHERE c.community_id = e.community_id
          AND c.kind = 'subgroup'
          AND c.subgroup_id = e.subgroup_id
          AND e.visibility = 'subgroup'
        """
    )
    op.execute(
        """
        UPDATE events e
        SET calendar_id = c.id
        FROM calendars c
        WHERE c.community_id = e.community_id
          AND c.kind = 'personal'
          AND c.owner_id = e.author_id
          AND e.visibility = 'private'
          AND e.calendar_id IS NULL
        """
    )
    op.execute(
        """
        UPDATE events e
        SET calendar_id = c.id
        FROM calendars c
        WHERE c.community_id = e.community_id
          AND c.kind = 'community'
          AND e.calendar_id IS NULL
        """
    )


def downgrade() -> None:
    op.drop_index("events_calendar_idx", table_name="events")
    op.drop_column("events", "calendar_id")
    op.drop_index("calendars_community_kind_idx", table_name="calendars")
    op.drop_index("calendars_subgroup_idx", table_name="calendars")
    op.drop_index("calendars_owner_idx", table_name="calendars")
    op.drop_index("calendars_one_community_per_community", table_name="calendars")
    op.drop_index("calendars_one_per_subgroup", table_name="calendars")
    op.drop_index("calendars_one_personal_per_user", table_name="calendars")
    op.drop_table("calendars")
