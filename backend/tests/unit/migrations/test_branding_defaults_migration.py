"""
@file tests/unit/migrations/test_branding_defaults_migration.py
@brief Branding default migrations chain to head; model and schema defaults match
       the current (Aegean, 0040) palette.
"""

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

from app.models.branding import CommunityBranding
from app.schemas.branding import BrandingResponse

BACKEND = Path(__file__).resolve().parents[3]
REV = "0033_branding_glass_defaults"

NEW_DEFAULTS = {
    "color_primary": "#24323D",
    "color_primary_dark": "#F1EBE4",
    "color_accent": "#2F5873",
    "color_surface_light": "#FBF9F6",
    "color_surface_dark": "#1C2834",
    "color_text_light": "#24323D",
    "color_text_dark": "#F1EBE4",
    "font_family": "Outfit",
}


def test_migration_parent_and_head() -> None:
    """@brief 0033 revises 0032_home_glass_bento and is on the head's chain."""
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    script = ScriptDirectory.from_config(cfg)
    rev = script.get_revision(REV)
    assert rev is not None
    assert rev.down_revision == "0032_home_glass_bento"
    heads = script.get_heads()
    assert len(heads) == 1
    assert REV in {r.revision for r in script.iterate_revisions(heads[0], "base")}


def test_aegean_defaults_migration_is_head_chain() -> None:
    """@brief 0040 revises 0039 and lies on the head's chain."""
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    script = ScriptDirectory.from_config(cfg)
    rev = script.get_revision("0040_aegean_branding_defaults")
    assert rev is not None and rev.down_revision == "0039_group_tags"
    heads = script.get_heads()
    assert "0040_aegean_branding_defaults" in {
        r.revision for r in script.iterate_revisions(heads[0], "base")
    }


def test_model_server_defaults_are_new_palette() -> None:
    """@brief CommunityBranding server defaults equal the glass palette."""
    cols = CommunityBranding.__table__.c
    for name, value in NEW_DEFAULTS.items():
        assert cols[name].server_default.arg == value, name


def test_schema_fallbacks_are_new_palette() -> None:
    """@brief BrandingResponse field fallbacks equal the glass palette."""
    resp = BrandingResponse(
        community_name="x", color_primary="#000000", color_primary_dark="#000000"
    )
    for name, value in NEW_DEFAULTS.items():
        if name in ("color_primary", "color_primary_dark"):
            continue
        assert getattr(resp, name) == value, name
