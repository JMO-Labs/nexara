"""aegean_branding_defaults: move branding color defaults to the Aegean palette

Branding colors are always sent to the client and override the theme, so
rows still holding the old built-in defaults move to the new ones; custom
colors an admin picked are left alone.

Revision ID: 0040_aegean_branding_defaults
Revises: 0039_group_tags
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0040_aegean_branding_defaults"
down_revision: str | Sequence[str] | None = "0039_group_tags"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# column -> (old default, new default)
COLORS = {
    "color_primary": ("#10141A", "#24323D"),
    "color_primary_dark": ("#E9ECF2", "#F1EBE4"),
    "color_accent": ("#3B5E9E", "#2F5873"),
    "color_surface_light": ("#F5F6F9", "#FBF9F6"),
    "color_surface_dark": ("#1A202A", "#1C2834"),
    "color_text_light": ("#10141A", "#24323D"),
    "color_text_dark": ("#E9ECF2", "#F1EBE4"),
}


def _move(direction: int) -> None:
    for col, pair in COLORS.items():
        old, new = pair[::direction]
        op.alter_column("community_branding", col, server_default=new)
        op.execute(
            f"UPDATE community_branding SET {col} = '{new}' WHERE upper({col}) = '{old}'"  # noqa: S608
        )


def upgrade() -> None:
    """@brief New defaults; untouched rows follow."""
    _move(1)


def downgrade() -> None:
    """@brief Back to the previous defaults."""
    _move(-1)
