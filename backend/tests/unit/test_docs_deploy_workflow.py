"""@file Validates the docs-deploy GitHub Actions workflow (nexara#123)."""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]


def _load() -> dict:
    for p in (".github/workflows/docs-deploy.yml", "wq-workflows/docs-deploy.yml"):
        f = ROOT / p
        if f.exists():
            return yaml.safe_load(f.read_text())
    raise AssertionError("docs-deploy.yml not found")


def test_triggers_main_push_and_dispatch() -> None:
    on = _load()[True]  # YAML parses bare `on` as True
    assert on["push"]["branches"] == ["main"]
    assert "workflow_dispatch" in on


def test_build_runs_script_and_uploads_pages_artifact() -> None:
    steps = _load()["jobs"]["build"]["steps"]
    assert any("scripts/build-docs-site.sh" in s.get("run", "") for s in steps)
    up = [s for s in steps if s.get("uses", "").startswith("actions/upload-pages-artifact")]
    assert up and up[0]["with"]["path"] == "docs/site/"


def test_deploy_needs_build_with_pages_perms_and_url() -> None:
    d = _load()["jobs"]["deploy"]
    assert d["needs"] == "build"
    assert d["permissions"] == {"pages": "write", "id-token": "write"}
    assert "page_url" in d["environment"]["url"]
    assert any(s.get("uses", "").startswith("actions/deploy-pages") for s in d["steps"])
