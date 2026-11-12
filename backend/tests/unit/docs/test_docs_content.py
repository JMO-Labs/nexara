"""
@file test_docs_content.py
@brief Guards README badges/links and refreshed setup/development docs.
"""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
README = (ROOT / "README.md").read_text()
GETTING = (ROOT / "docs/docs/getting-started.md").read_text()
DEV = (ROOT / "docs/docs/development.md").read_text()


def test_readme_docs_link_and_badges():
    assert "https://jmo-labs.github.io/nexara" in README
    assert "img.shields.io/badge/docs-latest-blue" in README
    assert "img.shields.io/badge/license-GPL--3.0-blue" in README
    assert "actions/workflows/docs-deploy.yml/badge.svg" in README


def test_readme_mentions_github_pages_deployment():
    assert "GitHub Pages" in README.split("## Deployment")[1]


@pytest.mark.parametrize(
    "cmd",
    [
        "git clone https://github.com/JMO-Labs/nexara.git",
        "uv venv .venv && source .venv/bin/activate && uv sync",
        "npm install",
        "alembic upgrade head",
        "uvicorn app.main:app --reload --port 8000",
        "npm run dev",
        "http://localhost:3000/app",
        "Troubleshooting",
    ],
)
def test_getting_started_commands(cmd):
    assert cmd in GETTING


@pytest.mark.parametrize(
    "term",
    ["Next.js 16", "Tailwind v4", "shadcn", "pytest-asyncio", "alembic", "mypy app/",
     "npx playwright test", "Conventional Commits"],
)
def test_development_current_tech(term):
    assert term in DEV


@pytest.mark.parametrize("stale", ["Nuxt", "Pinia", "Flowbite", "Vue Test Utils"])
def test_no_stale_references(stale):
    assert stale not in DEV + GETTING + README
