"""
@file test_build_docs_site.py
@brief Exercises scripts/build-docs-site.sh with stubbed mkdocs/doxygen.
"""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "scripts" / "build-docs-site.sh"
CHECKER = ROOT / "scripts" / "check-site-links.py"


def _stub(bin_dir: Path, name: str, body: str) -> None:
    p = bin_dir / name
    p.write_text("#!/usr/bin/env bash\n" + body + "\n")
    p.chmod(0o755)


def _run(
    tmp_path: Path,
    mkdocs_rc: int = 0,
    doxygen: bool = True,
    cov: bool = True,
    index_html: str = "",
):
    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True)
    (repo / "docs").mkdir()
    (repo / "scripts" / "generate-api-ref.sh").write_text(
        '#!/usr/bin/env bash\ntouch "$ROOT_MARK"\n'
    )
    (repo / "docs" / "mkdocs.yml").write_text("site_name: x\n")
    (repo / "docs" / "Doxyfile").write_text("")
    if cov:
        (repo / "coverage").mkdir()
        (repo / "coverage" / "index.html").write_text("c")
    (repo / "scripts" / "build-docs-site.sh").write_text(SCRIPT.read_text())
    (repo / "scripts" / "check-site-links.py").write_text(CHECKER.read_text())
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _stub(
        bin_dir,
        "mkdocs",
        f"[ {mkdocs_rc} -ne 0 ] && exit {mkdocs_rc}\n"
        f'echo "$@" > "{tmp_path}/mkdocs-args"\n'
        'while [ $# -gt 0 ]; do [ "$1" = -d ] && mkdir -p "$2" '
        f"&& echo '{index_html}' > \"$2/index.html\"; shift; done",
    )
    if doxygen:
        _stub(bin_dir, "doxygen", "mkdir -p build/api && touch build/api/index.html")
    env = {
        "PATH": f"{bin_dir}:/usr/local/bin:/usr/bin:/bin",
        "SKIP_INSTALL": "1",
        "ROOT_MARK": str(tmp_path / "api-ran"),
    }
    r = subprocess.run(
        ["bash", str(repo / "scripts" / "build-docs-site.sh")],
        env=env,
        capture_output=True,
        text=True,
        cwd=repo,
    )
    return r, repo


def test_success_builds_site_with_api_python_and_coverage(tmp_path):
    r, repo = _run(tmp_path)
    assert r.returncode == 0, r.stderr
    site = repo / "docs" / "site"
    assert (site / "index.html").exists()
    assert (site / "api-python" / "index.html").exists()
    assert (site / "coverage" / "index.html").exists()
    assert (tmp_path / "api-ran").exists()


def test_mkdocs_runs_strict(tmp_path):
    r, _ = _run(tmp_path)
    assert r.returncode == 0, r.stderr
    assert "--strict" in (tmp_path / "mkdocs-args").read_text()


def test_broken_internal_link_fails_build(tmp_path):
    r, _ = _run(tmp_path, index_html='<a href="missing/">x</a>')
    assert r.returncode != 0
    assert "missing/" in r.stdout


def test_mkdocs_failure_exits_nonzero(tmp_path):
    r, _ = _run(tmp_path, mkdocs_rc=3)
    assert r.returncode != 0


def test_missing_doxygen_and_coverage_are_skipped(tmp_path):
    r, repo = _run(tmp_path, doxygen=False, cov=False)
    assert r.returncode == 0, r.stderr
    assert not (repo / "docs" / "site" / "api-python").exists()
    assert not (repo / "docs" / "site" / "coverage").exists()


def test_gitignore_covers_build_outputs():
    lines = (ROOT / ".gitignore").read_text().splitlines()
    assert "docs/site/" in lines
    assert "html/" in lines
