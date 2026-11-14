"""
@file test_lists_api_doc.py
@brief Guards the Lists and List templates API docs against their routers (nexara#240).
"""

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
DOCS_DIR = ROOT / "docs/docs/developer"
DOC = DOCS_DIR / "lists-api.md"
TEMPLATES_DOC = DOCS_DIR / "list-templates-api.md"
ROUTERS = {
    "/lists": (ROOT / "backend/app/api/v1/lists.py", DOC),
    "/list_templates": (ROOT / "backend/app/api/v1/list_templates.py", TEMPLATES_DOC),
}


def _routes() -> list[tuple[str, Path]]:
    """@brief ``(METHOD /api/v1<prefix><path>, doc)`` for every @router.<verb>(...) decorator."""
    out = []
    for prefix, (path, doc) in ROUTERS.items():
        for node in ast.walk(ast.parse(path.read_text())):
            if not isinstance(node, ast.AsyncFunctionDef):
                continue
            for dec in node.decorator_list:
                if (
                    isinstance(dec, ast.Call)
                    and isinstance(dec.func, ast.Attribute)
                    and isinstance(dec.func.value, ast.Name)
                    and dec.func.value.id == "router"
                ):
                    sub = dec.args[0].value  # type: ignore[attr-defined]
                    out.append((f"{dec.func.attr.upper()} /api/v1{prefix}{sub}", doc))
    return out


def test_router_parse_finds_routes() -> None:
    assert len(_routes()) >= 20


@pytest.mark.parametrize(
    ("route", "doc"), _routes(), ids=lambda v: v.name if isinstance(v, Path) else v
)
def test_every_route_documented(route: str, doc: Path) -> None:
    assert f"### `{route}`" in doc.read_text()


def test_auth_and_error_envelope_documented() -> None:
    text = DOC.read_text()
    assert "Authorization: Bearer" in text
    assert '"error": {' in text
    for key in ('"code"', '"message"', '"details"'):
        assert key in text
    for code in ("NOT_FOUND", "AUTHORIZATION_ERROR", "VALIDATION_ERROR", "NO_SLOTS"):
        assert code in text


@pytest.mark.parametrize("doc", [DOC, TEMPLATES_DOC], ids=lambda p: p.name)
def test_each_route_has_auth_and_json_example(doc: Path) -> None:
    sections = doc.read_text().split("\n### `")[1:]
    assert sections
    for sec in sections:
        head = sec.splitlines()[0]
        assert "**Auth:**" in sec, head
        assert "```json" in sec or "204 No Content" in sec, head


@pytest.mark.parametrize("doc", [DOC, TEMPLATES_DOC], ids=lambda p: p.name)
def test_doc_under_500_lines(doc: Path) -> None:
    assert len(doc.read_text().splitlines()) < 500
