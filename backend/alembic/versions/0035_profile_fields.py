"""profile fields: contact, links, emergency contact, skills, availability,
dietary; per-field visibility on user_settings

Revision ID: 0035_profile_fields
Revises: 0034_perf_indexes
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0035_profile_fields"
down_revision: str | Sequence[str] | None = "0034_perf_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TEXT = ("phone", "contact_email", "address", "availability", "dietary")


def upgrade() -> None:
    """@brief Add optional profile columns and the field_visibility map."""
    for col in _TEXT:
        op.add_column("users", sa.Column(col, sa.Text(), nullable=True))
    op.add_column("users", sa.Column("links", JSONB(), nullable=False, server_default="[]"))
    op.add_column("users", sa.Column("emergency_contact", JSONB(), nullable=True))
    op.add_column("users", sa.Column("skills", JSONB(), nullable=False, server_default="[]"))
    op.add_column(
        "user_settings",
        sa.Column("field_visibility", JSONB(), nullable=False, server_default="{}"),
    )


def downgrade() -> None:
    """@brief Drop the profile columns."""
    op.drop_column("user_settings", "field_visibility")
    for col in ("skills", "emergency_contact", "links", *_TEXT):
        op.drop_column("users", col)
