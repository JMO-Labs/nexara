"""Daily question bank, per-prompt uses, reveal-after-answer prompts.

@file 0051_daily_questions.py
@brief Add question_bank, question_bank_uses, prompts.reveal_after_answer and
       one daily_question prompt per community.

Revision ID: 0051_daily_questions
Revises: 0050_features_tz
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0051_daily_questions"
down_revision = "0050_features_tz"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """@brief Create tables/column and insert the per-community daily prompt."""
    op.create_table(
        "question_bank",
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
            server_default=sa.text("'00000000-0000-0000-0000-000000000001'"),
        ),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="approved"),
        sa.Column(
            "suggested_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
        sa.Column("used_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("char_length(text) <= 280", name="question_bank_text_len_ck"),
        sa.CheckConstraint(
            "source IN ('builtin','admin','member')", name="question_bank_source_ck"
        ),
        sa.CheckConstraint(
            "status IN ('approved','pending','rejected')", name="question_bank_status_ck"
        ),
    )
    op.create_index(
        "question_bank_pick_idx", "question_bank", ["community_id", "status", "used_at"]
    )
    op.create_table(
        "question_bank_uses",
        sa.Column(
            "prompt_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("prompts.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "question_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("question_bank.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "used_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.add_column(
        "prompts",
        sa.Column("reveal_after_answer", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.execute(
        """
        INSERT INTO prompts (community_id, title, body, source, frequency_type, active_days,
                             scope, prompt_type, reveal_after_answer, notify_members,
                             generate_summary, created_by)
        SELECT c.id, 'Daily question', 'Today''s question', 'builtin', 'daily', 1,
               'community', 'daily_question', true, false, false,
               (SELECT u.id FROM users u
                 WHERE u.community_id = c.id AND u.role IN ('admin', 'owner')
                 ORDER BY u.created_at LIMIT 1)
        FROM communities c
        """
    )


def downgrade() -> None:
    """@brief Remove daily prompts, the column and both tables."""
    op.execute("DELETE FROM prompts WHERE prompt_type = 'daily_question'")
    op.drop_column("prompts", "reveal_after_answer")
    op.drop_table("question_bank_uses")
    op.drop_index("question_bank_pick_idx", table_name="question_bank")
    op.drop_table("question_bank")
