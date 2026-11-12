#!/usr/bin/env python3
"""
@file scripts/check-site-links.py
@brief Validate internal links and #fragments in a built docs site (stdlib only).

Usage: check-site-links.py [SITE_DIR]   (default: docs/site)
Exits 1 listing "file: link (reason)" for each broken internal link.
External http(s) links are only reported as warnings; mailto:/tel:/data: skipped.
"""

import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


class _Page(HTMLParser):
    """@brief Collects anchor hrefs and element ids from one HTML file."""

    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []
        self.ids: set[str] = set()

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"):
            self.ids.add(a["id"])
        if tag == "a" and a.get("name"):
            self.ids.add(a["name"])
        if tag == "a" and a.get("href") is not None:
            self.links.append(a["href"])


def _parse(path: Path) -> _Page:
    page = _Page()
    page.feed(path.read_text(encoding="utf-8", errors="replace"))
    return page


def _resolve(site: Path, src: Path, url_path: str) -> Path | None:
    """@brief Map a relative URL path to an existing file under site, or None."""
    base = site if url_path.startswith("/") else src.parent
    target = (base / unquote(url_path).lstrip("/")).resolve()
    if site.resolve() not in (target, *target.parents):
        return None
    if target.is_dir():
        target = target / "index.html"
    return target if target.is_file() else None


def check(site: Path) -> tuple[list[str], list[str]]:
    """@brief Return (errors, warnings) for all HTML files under site."""
    pages = {p: _parse(p) for p in sorted(site.rglob("*.html"))}
    errors: list[str] = []
    warnings: list[str] = []
    for src, page in pages.items():
        rel = src.relative_to(site)
        for link in page.links:
            u = urlsplit(link.strip())
            if u.scheme in ("http", "https"):
                warnings.append(f"{rel}: {link} (external, not checked)")
                continue
            if u.scheme or u.netloc:
                continue  # mailto:, tel:, data:, protocol-relative
            if not u.path:
                target = src
            else:
                target = _resolve(site, src, u.path)
                if target is None:
                    errors.append(f"{rel}: {link} (file not found)")
                    continue
            frag = unquote(u.fragment)
            if frag and frag != "top" and target.suffix == ".html":
                tp = pages.get(target.resolve()) or pages.get(target) or _parse(target)
                if frag not in tp.ids:
                    errors.append(f"{rel}: {link} (missing fragment #{frag})")
    return errors, warnings


def main(argv: list[str]) -> int:
    site = Path(argv[1] if len(argv) > 1 else "docs/site")
    if not site.is_dir():
        print(f"site dir not found: {site}")
        return 1
    errors, warnings = check(site)
    for w in warnings:
        print(f"WARN {w}")
    for e in errors:
        print(f"ERROR {e}")
    print(f"{len(errors)} broken internal link(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
