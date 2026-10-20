"""purge dm chat activity

Revision ID: 9db194555fd0
Revises: a1b2c3d4e5f6
Create Date: 2026-10-20 09:51:57.195060

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9db194555fd0"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """@brief Delete chat activity recorded for direct (DM) channels."""
    op.execute(
        "DELETE FROM activity_events WHERE verb = 'chat.posted' AND target_id IN "
        "(SELECT id FROM chat_channels WHERE channel_type = 'direct')"
    )


def downgrade() -> None:
    """@brief Irreversible data purge; nothing to restore."""
