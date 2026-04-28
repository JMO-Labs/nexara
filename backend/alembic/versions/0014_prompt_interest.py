"""prompt interest-capture fields

Revision ID: 0014_prompt_interest
Revises: 0013
"""
from alembic import op
import sqlalchemy as sa

revision = "0014_prompt_interest"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "prompts",
        sa.Column("prompt_type", sa.String(32), server_default=sa.text("'standard'"), nullable=False),
    )
    op.add_column("prompts", sa.Column("interest_category_slug", sa.String(64), nullable=True))
    op.add_column("prompts", sa.Column("interest_capture_hint", sa.Text(), nullable=True))
    op.create_index("ix_prompts_prompt_type", "prompts", ["prompt_type"])


def downgrade() -> None:
    op.drop_index("ix_prompts_prompt_type", table_name="prompts")
    op.drop_column("prompts", "interest_capture_hint")
    op.drop_column("prompts", "interest_category_slug")
    op.drop_column("prompts", "prompt_type")
