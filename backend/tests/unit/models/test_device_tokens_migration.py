"""
@file test_device_tokens_migration.py
@brief Verify the device_tokens migration sits on the single alembic head (nexara#215).
"""

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

BACKEND = Path(__file__).resolve().parents[3]


def _script() -> ScriptDirectory:
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    return ScriptDirectory.from_config(cfg)


def test_device_tokens_migration_is_single_head_after_pronouns() -> None:
    """@brief 0025_device_tokens chains after 0024_nudges on the single head."""
    script = _script()
    heads = script.get_heads()
    assert len(heads) == 1
    ancestors = {r.revision for r in script.iterate_revisions(heads[0], "base")}
    assert {"0025_device_tokens", "0025_plugin_api_keys"} <= ancestors
    rev = script.get_revision("0025_device_tokens")
    assert rev.down_revision == "0024_nudges"
