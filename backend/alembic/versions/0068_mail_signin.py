"""Mail settings (SMTP on communities) and sign-in tracking.

@file 0068_mail_signin.py
@brief Add communities.smtp_* columns and the signin_events table.

Revision ID: 0068_mail_signin
Revises: 0067_prompt_answer_recount
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import INET, UUID

from alembic import op

revision = "0068_mail_signin"
down_revision = "0067_prompt_answer_recount"
branch_labels = None
depends_on = None

_SMTP_TEXT_COLS = (
    "smtp_host",
    "smtp_user",
    "smtp_password",  # Fernet
    "smtp_from",
    "smtp_from_name",
    "smtp_google_refresh",  # Fernet
    "smtp_google_client_id",  # admin-entered Google OAuth client (env GOOGLE_MAIL_* otherwise)
    "smtp_google_client_secret",  # Fernet
    "smtp_last_error",
)


def _upgrade_mail() -> None:
    """@brief communities.smtp_* columns (DB row overrides env SMTP_*)."""
    for col in _SMTP_TEXT_COLS:
        op.add_column("communities", sa.Column(col, sa.Text(), nullable=True))
    op.add_column("communities", sa.Column("smtp_port", sa.Integer(), nullable=True))
    op.add_column("communities", sa.Column("smtp_security", sa.Text(), nullable=True))
    op.add_column(
        "communities",
        sa.Column("smtp_auth", sa.Text(), nullable=False, server_default="password"),
    )
    op.add_column(
        "communities", sa.Column("smtp_last_ok_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_check_constraint(
        "ck_communities_smtp_security",
        "communities",
        "smtp_security IN ('starttls','ssl','none')",
    )
    op.create_check_constraint(
        "ck_communities_smtp_auth", "communities", "smtp_auth IN ('password','google_oauth')"
    )


def _downgrade_mail() -> None:
    """@brief Drop communities.smtp_* columns."""
    op.drop_constraint("ck_communities_smtp_auth", "communities", type_="check")
    op.drop_constraint("ck_communities_smtp_security", "communities", type_="check")
    for col in ("smtp_last_ok_at", "smtp_auth", "smtp_security", "smtp_port", *_SMTP_TEXT_COLS):
        op.drop_column("communities", col)


def _upgrade_signin() -> None:
    """@brief signin_events: per-attempt sign-in log (90-day retention)."""
    op.create_table(
        "signin_events",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "community_id", UUID(as_uuid=True), sa.ForeignKey("communities.id"), nullable=False
        ),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("email_tried", sa.Text()),
        sa.Column("method", sa.Text(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.Text()),
        sa.Column("ip", INET()),
        sa.Column("user_agent", sa.Text()),
        sa.Column("device", sa.Text()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "method IN ('password','totp','recovery','passkey','magic_link','sso')",
            name="ck_signin_events_method",
        ),
    )
    op.create_index(
        "ix_signin_events_community_created",
        "signin_events",
        ["community_id", sa.text("created_at DESC")],
    )
    op.create_index("ix_signin_events_ip_created", "signin_events", ["ip", "created_at"])


def _downgrade_signin() -> None:
    """@brief Drop signin_events."""
    op.drop_table("signin_events")


def upgrade() -> None:
    """@brief Apply all 0068 changes."""
    _upgrade_mail()
    _upgrade_signin()


def downgrade() -> None:
    """@brief Revert all 0068 changes."""
    _downgrade_signin()
    _downgrade_mail()
