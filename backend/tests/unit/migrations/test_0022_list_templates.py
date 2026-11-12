"""
@file tests/unit/migrations/test_0022_list_templates.py
@brief Static checks for migration 0022 (list templates schema + seeds).
"""

import importlib.util
from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory

VERSIONS = Path(__file__).resolve().parents[3] / "alembic" / "versions"
FILE = VERSIONS / "0022_list_templates.py"


@pytest.fixture(scope="module")
def mig():
    assert FILE.exists(), "0022_list_templates.py missing"
    spec = importlib.util.spec_from_file_location("mig0022", FILE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_revision_chain(mig) -> None:
    assert mig.revision == "0022_list_templates"
    assert mig.down_revision == "0021_add_subgroup_accent_color"


def test_single_head_is_list_templates() -> None:
    """@brief The migration chain must have exactly one head: this revision."""
    cfg = Config()
    cfg.set_main_option("script_location", str(VERSIONS.parent))
    assert ScriptDirectory.from_config(cfg).get_heads() == ["0022_list_templates"]


def test_ten_notification_columns(mig) -> None:
    cols = mig.NOTIF_COLUMNS
    assert len(cols) == 10
    assert "notif_list_member_email" in cols
    assert all(c.startswith("notif_list_") for c in cols)


def test_four_system_templates(mig) -> None:
    seeds = mig.SEED_TEMPLATES
    assert [s["category"] for s in seeds] == ["gift", "potluck", "todo", "contact"]
    for s in seeds:
        keys = [f["key"] for f in s["fields"]]
        assert keys and len(keys) == len(set(keys))
    assert any(f["type_key"] == "user_pull" for f in seeds[3]["fields"])
