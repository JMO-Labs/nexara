"""calendar polish: ical token, reminders, sync conflict, admin shared subs

Revision ID: 0013
Revises: 0012
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "events",
        sa.Column(
            "reminder_offsets_minutes",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[60]'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "calendar_subscriptions",
        sa.Column("locally_modified", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "calendar_subscriptions",
        sa.Column("shared_by_admin", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "calendar_subscriptions",
        sa.Column("sync_interval_minutes", sa.Integer(), server_default=sa.text("60"), nullable=False),
    )
    op.create_table(
        "calendar_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(128), nullable=False, unique=True),
        sa.Column("scope", sa.String(32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_calendar_tokens_user", "calendar_tokens", ["user_id"])


def downgrade() -> None:
    op.drop_table("calendar_tokens")
    op.drop_column("calendar_subscriptions", "sync_interval_minutes")
    op.drop_column("calendar_subscriptions", "shared_by_admin")
    op.drop_column("calendar_subscriptions", "locally_modified")
    op.drop_column("events", "reminder_offsets_minutes")
