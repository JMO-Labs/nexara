"""
@file test_docs_nav.py
@brief Guards the directory-based MkDocs nav (awesome-pages) structure.
"""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
DOCS = ROOT / "docs" / "docs"
PAGES = [
    "user/index.md",
    "user/self-hosting.md",
    "user/features.md",
    "user/faq.md",
    "developer/index.md",
    "developer/architecture.md",
    "developer/contributing.md",
]


def test_mkdocs_has_no_explicit_nav_and_uses_awesome_pages():
    text = (ROOT / "docs" / "mkdocs.yml").read_text()
    assert not any(line.startswith("nav:") for line in text.splitlines())
    assert "awesome-pages" in text


@pytest.mark.parametrize("d", ["", "user", "developer"])
def test_pages_files_exist(d):
    assert (DOCS / d / ".pages").is_file()


@pytest.mark.parametrize("page", PAGES)
def test_content_pages_are_substantive(page):
    path = DOCS / page
    assert path.is_file()
    assert len(path.read_text().split()) >= 150


@pytest.mark.parametrize("d", ["", "user", "developer"])
def test_pages_lists_reference_existing_entries(d):
    for line in (DOCS / d / ".pages").read_text().splitlines():
        if line.startswith("  - References"):
            break  # external link block (api/, coverage/) is built by CI
        if line.strip() == "- ...":
            continue  # awesome-pages rest entry
        if line.strip().startswith("- ") and ":" not in line:
            assert (DOCS / d / line.strip()[2:]).exists()


def test_root_references_are_relative():
    text = (DOCS / ".pages").read_text()
    assert ": /" not in text


def test_pages_job_builds_strict():
    text = (ROOT / ".gitlab" / "ci" / "pages.yml").read_text()
    assert "mkdocs build --strict" in text


def test_docs_build_job_runs_on_mr_and_dev():
    text = (ROOT / ".gitlab" / "ci" / "pages.yml").read_text()
    assert "\ndocs:build:" in text
    job = text.split("\ndocs:build:")[1].split("\npages:")[0]
    assert "stage: test" in job
    assert "mkdocs build --strict" in job
    assert "mkdocs-awesome-pages-plugin" in job
    assert "docs/**" in job
    assert "$CI_MERGE_REQUEST_IID" in job


def _nav_entries(d):
    """@brief Top-level nav entries of a dir's .pages (before References)."""
    entries = []
    for line in (DOCS / d / ".pages").read_text().splitlines():
        if line.startswith("  - References"):
            break
        if line.startswith("  - "):
            entries.append(line[4:].strip())
    return entries


@pytest.mark.parametrize("d", ["", "user", "developer"])
def test_all_pages_reachable_in_nav(d):
    entries = _nav_entries(d)
    if "..." in entries:
        return
    missing = [p.name for p in (DOCS / d).glob("*.md") if p.name not in entries]
    assert not missing, f"{d or 'root'}: not in nav: {missing}"


@pytest.mark.parametrize("d", ["", "user", "developer"])
def test_pages_nav_has_rest_entry(d):
    assert "..." in _nav_entries(d)


def test_api_reference_link_is_relative():
    text = (DOCS / "developer" / "api-reference.md").read_text()
    assert "](/" not in text
