"""Monitoring: audit_log action index and per-community audit retention.

@file 0073_monitoring.py
@brief Adds audit_log(action) index and communities.audit_retention_days.

audit_log has no community_id (single-community instance) and already has a
created_at desc index, so only the action index is added.

Revision ID: 0073_monitoring
Revises: 0072_push_devices
"""

import sqlalchemy as sa

from alembic import op

revision = "0073_monitoring"
down_revision = "0072_push_devices"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """@brief Add index and retention column."""
    op.create_index("audit_log_action_idx", "audit_log", ["action"])
    op.add_column(
        "communities",
        sa.Column("audit_retention_days", sa.Integer(), nullable=False, server_default="365"),
    )


def downgrade() -> None:
    """@brief Drop index and column."""
    op.drop_column("communities", "audit_retention_days")
    op.drop_index("audit_log_action_idx", table_name="audit_log")
