"""notifications v2 foundation: JSONB prefs + grouped notification columns.

Revision ID: b2c3d4e5f6a7
Revises: 0025_plugin_api_keys
Create Date: 2026-05-02
"""

import json
import re
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: str | Sequence[str] | None = "0025_plugin_api_keys"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CHANNELS = ("inapp", "email", "push", "toast")

# Built-in type defaults (spec section 5.1).
_TYPE_DEFAULTS: dict[str, dict[str, bool]] = {
    "mention": {"inapp": True, "email": True, "push": True, "toast": True},
    "comment": {"inapp": True, "email": False, "push": False, "toast": True},
    "reaction": {"inapp": True, "email": False, "push": False, "toast": False},
    "new_post": {"inapp": True, "email": False, "push": False, "toast": False},
    "system": {"inapp": True, "email": True, "push": True, "toast": True},
    "invite_accepted": {"inapp": True, "email": True, "push": False, "toast": False},
    "event_reminder": {"inapp": True, "email": True, "push": True, "toast": True},
    "event_rsvp": {"inapp": True, "email": False, "push": False, "toast": False},
    "gallery_activity": {"inapp": True, "email": False, "push": False, "toast": False},
    "gallery_reminder": {"inapp": True, "email": True, "push": False, "toast": False},
    "prompt": {"inapp": True, "email": False, "push": False, "toast": True},
    "prompt_summary": {"inapp": True, "email": True, "push": False, "toast": False},
}

_LEGACY_RE = re.compile(r"^notif_(?P<type>\w+?)_(?P<channel>inapp|push|email)$")

# Legacy columns recreated on downgrade: (name, server default).
_LEGACY_COLS: tuple[tuple[str, bool], ...] = (
    ("notif_mention_inapp", True),
    ("notif_mention_push", True),
    ("notif_mention_email", True),
    ("notif_comment_inapp", True),
    ("notif_comment_push", True),
    ("notif_comment_email", True),
    ("notif_reaction_inapp", True),
    ("notif_reaction_push", True),
    ("notif_reaction_email", False),
    ("notif_new_post_inapp", True),
    ("notif_new_post_push", False),
    ("notif_new_post_email", False),
    ("notif_event_reminder_inapp", True),
    ("notif_event_reminder_push", True),
    ("notif_event_reminder_email", True),
    ("notif_event_rsvp_inapp", True),
    ("notif_event_rsvp_push", False),
    ("notif_event_rsvp_email", False),
    ("notif_gallery_activity_inapp", True),
    ("notif_gallery_activity_push", False),
    ("notif_gallery_activity_email", False),
    ("notif_dm_inapp", True),
    ("notif_dm_push", True),
    ("notif_dm_email", True),
    ("notif_prompt_inapp", True),
    ("notif_prompt_push", True),
    ("notif_prompt_email", False),
    ("notif_prompt_summary_inapp", True),
    ("notif_prompt_summary_push", False),
    ("notif_prompt_summary_email", False),
    ("notif_birthday_inapp", True),
    ("notif_birthday_push", False),
    ("notif_birthday_email", False),
    ("notif_system_inapp", True),
    ("notif_system_push", True),
    ("notif_system_email", True),
    ("notif_poll_inapp", True),
    ("notif_poll_push", False),
    ("notif_poll_email", False),
    ("notif_invite_accepted_inapp", True),
    ("notif_invite_accepted_push", True),
    ("notif_invite_accepted_email", False),
    ("notif_nudge_inapp", True),
    ("notif_nudge_push", False),
    ("notif_nudge_email", False),
)
_MUTE_COLS = ("mute_all_push", "mute_all_email")


def _build_prefs(row: dict[str, object]) -> dict[str, dict[str, bool]]:
    """@brief Merge type defaults with legacy per-channel values for one user."""
    prefs = {k: dict(v) for k, v in _TYPE_DEFAULTS.items()}
    for col, value in row.items():
        m = _LEGACY_RE.match(col)
        if m and value is not None and m["type"] in prefs:
            prefs[m["type"]][m["channel"]] = bool(value)
    return prefs


def upgrade() -> None:
    op.add_column("notifications", sa.Column("group_key", sa.Text(), nullable=True))
    op.add_column(
        "notifications",
        sa.Column("count", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "notifications",
        sa.Column(
            "actor_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=False,
            server_default=sa.text("'{}'::uuid[]"),
        ),
    )
    op.add_column(
        "notifications",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.add_column(
        "notifications", sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_index(
        "notifications_group_active_idx",
        "notifications",
        ["user_id", "group_key"],
        unique=True,
        postgresql_where=sa.text("group_key IS NOT NULL AND read_at IS NULL"),
    )
    op.create_index(
        "notifications_user_active_idx",
        "notifications",
        ["user_id", "dismissed_at", sa.text("created_at DESC")],
        postgresql_where=sa.text("dismissed_at IS NULL"),
    )

    jsonb_empty = sa.text("'{}'::jsonb")
    op.add_column(
        "user_settings",
        sa.Column(
            "notification_prefs", postgresql.JSONB(), nullable=False, server_default=jsonb_empty
        ),
    )
    op.add_column("user_settings", sa.Column("dnd_schedule", postgresql.JSONB(), nullable=True))
    op.add_column(
        "user_settings", sa.Column("dnd_until", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "user_settings",
        sa.Column("dnd_timezone", sa.Text(), nullable=False, server_default="UTC"),
    )
    op.add_column(
        "user_settings",
        sa.Column("digest_cadence", postgresql.JSONB(), nullable=False, server_default=jsonb_empty),
    )
    op.add_column(
        "user_settings",
        sa.Column("digest_last_sent_at", sa.DateTime(timezone=True), nullable=True),
    )

    bind = op.get_bind()
    legacy = [
        c["name"]
        for c in sa.inspect(bind).get_columns("user_settings")
        if _LEGACY_RE.match(c["name"])
    ]
    select = sa.text(f"SELECT user_id, {', '.join(legacy)} FROM user_settings")  # noqa: S608
    rows = bind.execute(select).mappings()
    update = sa.text(
        "UPDATE user_settings SET notification_prefs = CAST(:p AS jsonb) WHERE user_id = :uid"
    )
    for row in rows.all():
        bind.execute(update, {"p": json.dumps(_build_prefs(dict(row))), "uid": row["user_id"]})

    for col in (*legacy, *_MUTE_COLS):
        op.drop_column("user_settings", col)


def downgrade() -> None:
    for col, default in _LEGACY_COLS:
        op.add_column(
            "user_settings",
            sa.Column(
                col, sa.Boolean(), nullable=False, server_default=sa.text(str(default).lower())
            ),
        )
    for col in _MUTE_COLS:
        op.add_column(
            "user_settings",
            sa.Column(col, sa.Boolean(), nullable=False, server_default=sa.text("false")),
        )
    for col in (
        "digest_last_sent_at",
        "digest_cadence",
        "dnd_timezone",
        "dnd_until",
        "dnd_schedule",
        "notification_prefs",
    ):
        op.drop_column("user_settings", col)
    op.drop_index("notifications_user_active_idx", table_name="notifications")
    op.drop_index("notifications_group_active_idx", table_name="notifications")
    for col in ("dismissed_at", "updated_at", "actor_ids", "count", "group_key"):
        op.drop_column("notifications", col)
