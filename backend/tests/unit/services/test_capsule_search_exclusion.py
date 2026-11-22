"""
@file test_capsule_search_exclusion.py
@brief Sealed capsule text must never be searchable: no FTS column, no search reference.
"""

from pathlib import Path

from app.models.time_capsule import TimeCapsule


def test_capsules_have_no_search_column() -> None:
    assert not hasattr(TimeCapsule, "search_fts")


def test_search_modules_never_touch_capsules() -> None:
    repos = Path(__file__).resolve().parents[3] / "app" / "repositories"
    for f in repos.glob("search*.py"):
        assert "time_capsule" not in f.read_text().lower(), f.name
