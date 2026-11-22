"""Family recipe book.

@file 0055_recipes.py
@brief Add recipes, list_item.recipe_id and the 'recipe' tag target type.

Revision ID: 0055_recipes
Revises: 0053_recap_settings
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0055_recipes"
down_revision = "0053_recap_settings"
branch_labels = None
depends_on = None

_BASE = "'post','comment','media','list','event','chat_message'"


def upgrade() -> None:
    """@brief Create recipes, link column and widen the tag target check."""
    op.create_table(
        "recipes",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "community_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("communities.id", ondelete="CASCADE"),
            nullable=False,
            server_default=sa.text("'00000000-0000-0000-0000-000000000001'::uuid"),
        ),
        sa.Column(
            "author_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("story", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "ingredients", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")
        ),
        sa.Column(
            "steps", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")
        ),
        sa.Column("servings", sa.Integer(), nullable=True),
        sa.Column("prep_minutes", sa.Integer(), nullable=True),
        sa.Column("cook_minutes", sa.Integer(), nullable=True),
        sa.Column(
            "photo_media_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=False,
            server_default=sa.text("'{}'::uuid[]"),
        ),
        sa.Column(
            "best_maker_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "best_maker_household_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("household_members.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column("visibility", sa.Text(), nullable=False, server_default="community"),
        sa.Column(
            "subgroup_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("subgroups.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "search_fts",
            postgresql.TSVECTOR(),
            sa.Computed(
                "to_tsvector('english', coalesce(title,'') || ' ' || coalesce(story,'')"
                " || ' ' || coalesce(ingredients::text,''))",
                persisted=True,
            ),
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("char_length(title) <= 120", name="recipes_title_ck"),
        sa.CheckConstraint(
            "visibility IN ('community','subgroup','private')", name="recipes_visibility_ck"
        ),
    )
    op.create_index("ix_recipes_search_fts", "recipes", ["search_fts"], postgresql_using="gin")
    op.create_index("ix_recipes_tags", "recipes", ["tags"], postgresql_using="gin")
    op.create_index("ix_recipes_community_created", "recipes", ["community_id", "created_at"])
    op.add_column(
        "list_item",
        sa.Column(
            "recipe_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("recipes.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.drop_constraint("tags_target_type_ck", "tags", type_="check")
    op.create_check_constraint("tags_target_type_ck", "tags", f"target_type IN ({_BASE},'recipe')")


def downgrade() -> None:
    """@brief Reverse everything in upgrade."""
    op.execute("DELETE FROM tags WHERE target_type = 'recipe'")
    op.drop_constraint("tags_target_type_ck", "tags", type_="check")
    op.create_check_constraint("tags_target_type_ck", "tags", f"target_type IN ({_BASE})")
    op.drop_column("list_item", "recipe_id")
    op.drop_table("recipes")
