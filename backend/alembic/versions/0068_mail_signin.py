"""Mail settings (SMTP on communities) and sign-in tracking.

@file 0068_mail_signin.py
@brief Add communities.smtp_* columns. Task 4 appends signin_events below.

Revision ID: 0068_mail_signin
Revises: 0067_prompt_answer_recount
"""

import sqlalchemy as sa

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


def upgrade() -> None:
    """@brief Apply all 0068 changes."""
    _upgrade_mail()
    # Task 4: _upgrade_signin() goes here.


def downgrade() -> None:
    """@brief Revert all 0068 changes."""
    # Task 4: _downgrade_signin() goes here (before the mail columns).
    _downgrade_mail()
