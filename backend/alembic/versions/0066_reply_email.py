"""Reply by email: IMAP settings, reply tokens, reply log.

@file 0066_reply_email.py
@brief Add communities.inbound_* columns, reply_tokens and inbound_replies.

Revision ID: 0066_reply_email
Revises: 0063_stories
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0066_reply_email"
# ponytail: chained to 0063 in this worktree; orchestrator re-chains at merge.
down_revision = "0065_newsletter"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    """@brief Create the tables and columns."""
    op.add_column("communities", sa.Column("inbound_imap_host", sa.Text(), nullable=True))
    op.add_column(
        "communities",
        sa.Column("inbound_imap_port", sa.Integer(), nullable=False, server_default="993"),
    )
    op.add_column("communities", sa.Column("inbound_imap_user", sa.Text(), nullable=True))
    op.add_column("communities", sa.Column("inbound_imap_password", sa.Text(), nullable=True))
    op.add_column("communities", sa.Column("inbound_reply_address", sa.Text(), nullable=True))
    op.create_table(
        "reply_tokens",
        sa.Column("token_hash", sa.CHAR(64), primary_key=True),
        sa.Column(
            "community_id",
            _UUID,
            sa.ForeignKey("communities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", _UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("post_id", _UUID, sa.ForeignKey("posts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_reply_tokens_expires_at", "reply_tokens", ["expires_at"])
    op.create_table(
        "inbound_replies",
        sa.Column("id", _UUID, server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("user_id", _UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_inbound_replies_user_id", "inbound_replies", ["user_id"])


def downgrade() -> None:
    """@brief Drop everything added by upgrade()."""
    op.drop_table("inbound_replies")
    op.drop_table("reply_tokens")
    for col in (
        "inbound_reply_address",
        "inbound_imap_password",
        "inbound_imap_user",
        "inbound_imap_port",
        "inbound_imap_host",
    ):
        op.drop_column("communities", col)
