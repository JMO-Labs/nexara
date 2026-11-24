"""SSO sync: provider policy columns, claim_mapping as single source, member source.

@file 0071_sso_sync.py
@brief Adds oauth_providers preset/allowed_domains/required_group/username_claim/
sync_profile and subgroup_members.source; folds the per-column *_claim values
into claim_mapping (existing keys win) and drops the columns.

Revision ID: 0071_sso_sync
Revises: 0070_twofactor
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY

from alembic import op

revision = "0071_sso_sync"
down_revision = "0070_twofactor"
branch_labels = None
depends_on = None

# column -> (claim_mapping key, column default)
_CLAIMS = {
    "sub_claim": ("sub", "sub"),
    "email_claim": ("email", "email"),
    "name_claim": ("name", "name"),
    "avatar_claim": ("picture", "picture"),
    "group_claim": ("groups", "groups"),
}


def upgrade() -> None:
    """@brief Add columns, migrate *_claim into claim_mapping, drop them."""
    op.add_column("oauth_providers", sa.Column("preset", sa.Text(), nullable=True))
    op.add_column(
        "oauth_providers",
        sa.Column("allowed_domains", ARRAY(sa.Text()), nullable=False, server_default="{}"),
    )
    op.add_column("oauth_providers", sa.Column("required_group", sa.Text(), nullable=True))
    op.add_column(
        "oauth_providers",
        sa.Column("username_claim", sa.Text(), nullable=False, server_default="preferred_username"),
    )
    op.add_column(
        "oauth_providers",
        sa.Column("sync_profile", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.add_column(
        "subgroup_members",
        sa.Column("source", sa.Text(), nullable=False, server_default="manual"),
    )
    op.create_check_constraint(
        "subgroup_members_source_check", "subgroup_members", "source IN ('manual','sso')"
    )

    # Fold: columns first, then existing claim_mapping so its keys win.
    cols = [
        f"CASE WHEN {c} IS NOT NULL AND {c} <> '{d}' "
        f"THEN jsonb_build_object('{k}', {c}) ELSE '{{}}'::jsonb END"
        for c, (k, d) in _CLAIMS.items()
    ]
    op.execute(
        "UPDATE oauth_providers SET claim_mapping = "
        + " || ".join(f"({c})" for c in cols)
        + " || claim_mapping"
    )
    for col in _CLAIMS:
        op.drop_column("oauth_providers", col)


def downgrade() -> None:
    """@brief Restore *_claim columns from claim_mapping; drop new columns."""
    for col, (key, dflt) in _CLAIMS.items():
        op.add_column(
            "oauth_providers",
            sa.Column(col, sa.Text(), nullable=False, server_default=dflt),
        )
        op.execute(
            f"UPDATE oauth_providers SET {col} = claim_mapping->>'{key}' "
            f"WHERE jsonb_typeof(claim_mapping->'{key}') = 'string'"
        )
    op.drop_constraint("subgroup_members_source_check", "subgroup_members", type_="check")
    op.drop_column("subgroup_members", "source")
    for col in ("sync_profile", "username_claim", "required_group", "allowed_domains", "preset"):
        op.drop_column("oauth_providers", col)
