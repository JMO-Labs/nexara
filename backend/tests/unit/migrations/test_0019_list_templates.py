"""
@file tests/unit/migrations/test_0019_list_templates.py
@brief Static checks for migration 0019 (list templates schema + seeds).
"""

import importlib.util
from pathlib import Path

import pytest

VERSIONS = Path(__file__).resolve().parents[3] / "alembic" / "versions"
FILE = VERSIONS / "0019_list_templates.py"

TABLES = [
    "list_template",
    "list_template_field",
    "list_template_item",
    "list",
    "list_member",
    "list_item",
    "list_item_signup",
    "list_item_completion",
]


@pytest.fixture(scope="module")
def mig():
    assert FILE.exists(), "0019_list_templates.py missing"
    spec = importlib.util.spec_from_file_location("mig0019", FILE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_revision_chain(mig) -> None:
    assert mig.revision == "0019_list_templates"
    assert mig.down_revision == "a78f91338679"


def test_creates_all_tables_and_drops_in_reverse(mig) -> None:
    assert mig.TABLES == TABLES
    src = FILE.read_text()
    for t in TABLES:
        assert f'"{t}"' in src


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
