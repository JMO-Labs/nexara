"""Relations between members and household members.

@file 0060_relations.py
@brief Add the relations table with pair-unique indexes.

Revision ID: 0060_relations
Revises: 0059_chore_rotation
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0060_relations"
down_revision = "0059_chore_rotation"
branch_labels = None
depends_on = None

KINDS = "'parent','child','spouse','partner','sibling','friend','other'"


def upgrade() -> None:
    """@brief Create relations and its unique pair indexes."""
    uuid = postgresql.UUID(as_uuid=True)
    op.create_table(
        "relations",
        sa.Column("id", uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "community_id",
            uuid,
            sa.ForeignKey("communities.id", ondelete="CASCADE"),
            nullable=False,
            server_default=sa.text("'00000000-0000-0000-0000-000000000001'::uuid"),
        ),
        sa.Column(
            "from_user_id",
            uuid,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("to_user_id", uuid, sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column(
            "to_household_member_id",
            uuid,
            sa.ForeignKey("household_members.id", ondelete="CASCADE"),
        ),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("label", sa.Text()),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column(
            "created_by",
            uuid,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("confirmed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(f"kind IN ({KINDS})", name="ck_relations_kind"),
        sa.CheckConstraint("status IN ('pending','confirmed')", name="ck_relations_status"),
        sa.CheckConstraint("char_length(label) <= 40", name="ck_relations_label_len"),
        sa.CheckConstraint(
            "(to_user_id IS NULL) <> (to_household_member_id IS NULL)", name="ck_relations_one_to"
        ),
        sa.CheckConstraint(
            "to_user_id IS DISTINCT FROM from_user_id", name="ck_relations_not_self"
        ),
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_relations_user_pair ON relations "
        "(LEAST(from_user_id, to_user_id), GREATEST(from_user_id, to_user_id)) "
        "WHERE to_user_id IS NOT NULL"
    )
    op.create_index(
        "uq_relations_household",
        "relations",
        ["from_user_id", "to_household_member_id"],
        unique=True,
        postgresql_where=sa.text("to_household_member_id IS NOT NULL"),
    )
    op.create_index("ix_relations_from", "relations", ["community_id", "from_user_id"])
    op.create_index("ix_relations_to", "relations", ["community_id", "to_user_id"])


def downgrade() -> None:
    """@brief Drop relations and its indexes."""
    op.drop_table("relations")
