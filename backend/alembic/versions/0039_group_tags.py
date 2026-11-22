"""group_tags: @group tags on posts/comments and who may @ a group

Revision ID: 0039_group_tags
Revises: 0038_weather_places
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0039_group_tags"
down_revision: str | Sequence[str] | None = "0038_weather_places"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """@brief Allow subgroup tags; add subgroups.tag_policy."""
    op.add_column(
        "subgroups",
        sa.Column("tag_policy", sa.Text(), nullable=False, server_default="members"),
    )
    op.create_check_constraint(
        "subgroups_tag_policy_ck", "subgroups", "tag_policy IN ('members','admins')"
    )
    op.drop_constraint("tags_subject_type_ck", "tags", type_="check")
    op.create_check_constraint(
        "tags_subject_type_ck", "tags", "subject_type IN ('user','household','subgroup')"
    )


def downgrade() -> None:
    """@brief Drop group tags and the policy column."""
    op.execute("DELETE FROM tags WHERE subject_type = 'subgroup'")
    op.drop_constraint("tags_subject_type_ck", "tags", type_="check")
    op.create_check_constraint(
        "tags_subject_type_ck", "tags", "subject_type IN ('user','household')"
    )
    op.drop_constraint("subgroups_tag_policy_ck", "subgroups", type_="check")
    op.drop_column("subgroups", "tag_policy")
