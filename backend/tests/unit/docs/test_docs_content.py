"""@file Guards README/docs content required by nexara#112."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
README = (ROOT / "README.md").read_text()
DEV = (ROOT / "docs/docs/development.md").read_text()
START = (ROOT / "docs/docs/getting-started.md").read_text()


def test_readme_docs_link_and_badges() -> None:
    assert "https://jmo-labs.github.io/nexara" in README
    assert "img.shields.io/badge/docs-latest-blue" in README
    assert "img.shields.io/badge/license-GPL--3.0" in README
    assert "actions/workflows/docs-deploy.yml/badge.svg" in README
    assert "GitHub Pages" in README


def test_getting_started_commands() -> None:
    for cmd in (
        "git clone https://github.com/JMO-Labs/nexara.git",
        "uv venv .venv && source .venv/bin/activate && uv sync",
        "npm install",
        "alembic upgrade head",
        "uvicorn app.main:app --reload --port 8000",
        "npm run dev",
        "http://localhost:3000/app",
        "Troubleshooting",
    ):
        assert cmd in START


def test_development_current_stack_and_no_stale() -> None:
    for term in ("Next.js 16", "Tailwind v4", "shadcn", "pytest-asyncio", "alembic"):
        assert term in DEV
    for stale in ("Nuxt", "Pinia", "Flowbite", "Vue Test Utils"):
        assert stale not in DEV + START + README


def test_getting_started_cd_steps_are_root_relative() -> None:
    """Every cd into backend/frontend returns to root so blocks paste in order."""
    lines = [ln.strip() for ln in START.splitlines()]
    bare = [
        ln
        for ln in lines
        if ln.startswith(("cd backend", "cd frontend")) and not ln.endswith("&& cd ..")
    ]
    assert not bare, f"use (cd ... && ...) subshells: {bare}"
    assert "(cd backend && pytest --cov=app --cov-report=html -v)" in START
    assert "(cd frontend && npm test)" in START
    assert "from the repo root" in START
