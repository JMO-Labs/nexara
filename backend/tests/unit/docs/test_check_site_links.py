"""
@file test_check_site_links.py
@brief Tests for scripts/check-site-links.py (internal docs link checker).
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
CHECKER = ROOT / "scripts" / "check-site-links.py"


def _run(site: Path):
    return subprocess.run([sys.executable, str(CHECKER), str(site)], capture_output=True, text=True)


def _page(site: Path, name: str, body: str) -> None:
    p = site / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f"<html><body>{body}</body></html>")


def test_clean_site_passes(tmp_path):
    _page(
        tmp_path,
        "index.html",
        '<a href="a/">A</a><a href="a/#sec">S</a><a href="#top" >t</a><h1 id="top">x</h1>',
    )
    _page(tmp_path, "a/index.html", '<h2 id="sec">s</h2><a href="../">home</a>')
    r = _run(tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr


def test_missing_file_fails(tmp_path):
    _page(tmp_path, "index.html", '<a href="nope/">x</a>')
    r = _run(tmp_path)
    assert r.returncode != 0
    assert "index.html" in r.stdout and "nope/" in r.stdout


def test_missing_fragment_fails(tmp_path):
    _page(tmp_path, "index.html", '<a href="b.html#ghost">x</a>')
    _page(tmp_path, "b.html", '<p id="real">y</p>')
    r = _run(tmp_path)
    assert r.returncode != 0
    assert "#ghost" in r.stdout


def test_external_and_mailto_only_warn(tmp_path):
    _page(
        tmp_path,
        "index.html",
        '<a href="https://example.invalid/x">e</a><a href="mailto:a@b.c">m</a>',
    )
    r = _run(tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "example.invalid" in r.stdout + r.stderr
