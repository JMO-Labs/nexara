"""branding glass defaults: new palette server defaults, migrate untouched rows

Revision ID: 0033_branding_glass_defaults
Revises: 0032_home_glass_bento
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0033_branding_glass_defaults"
down_revision: str | Sequence[str] | None = "0032_home_glass_bento"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# column -> (old defaults, new default)
_COLUMNS: dict[str, tuple[tuple[str, ...], str]] = {
    "color_primary": (("#3b82f6",), "#10141A"),
    "color_primary_dark": (("#2563eb",), "#E9ECF2"),
    "color_accent": (("#C6B4F5", "#8b5cf6"), "#3B5E9E"),
    "color_surface_light": (("#ffffff",), "#F5F6F9"),
    "color_surface_dark": (("#1f2937",), "#1A202A"),
    "color_text_light": (("#111827",), "#10141A"),
    "color_text_dark": (("#f9fafb",), "#E9ECF2"),
    "font_family": (("Inter",), "Outfit"),
}
_OLD_DEFAULT = {c: olds[0] for c, (olds, _) in _COLUMNS.items()}


def _swap(col: str, froms: tuple[str, ...], to: str, ci: bool) -> None:
    """@brief Set column default and rewrite rows still equal to a given old value."""
    op.execute(f"ALTER TABLE community_branding ALTER COLUMN {col} SET DEFAULT '{to}'")
    lhs = f"lower({col})" if ci else col
    vals = ", ".join(f"'{(f.lower() if ci else f)}'" for f in froms)
    op.execute(f"UPDATE community_branding SET {col} = '{to}' WHERE {lhs} IN ({vals})")


def upgrade() -> None:
    for col, (olds, new) in _COLUMNS.items():
        _swap(col, olds, new, ci=col != "font_family")


def downgrade() -> None:
    for col, (olds, new) in _COLUMNS.items():
        old = _OLD_DEFAULT[col]
        op.execute(f"ALTER TABLE community_branding ALTER COLUMN {col} SET DEFAULT '{old}'")
        lhs = f"lower({col})" if col != "font_family" else col
        val = new.lower() if col != "font_family" else new
        op.execute(f"UPDATE community_branding SET {col} = '{old}' WHERE {lhs} = '{val}'")
