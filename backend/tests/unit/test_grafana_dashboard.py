"""
@file test_grafana_dashboard.py
@brief Structural validation of deploy/grafana/nexara-dashboard.json.
"""

import json
import re
from pathlib import Path

import pytest

PATH = Path(__file__).resolve().parents[3] / "deploy" / "grafana" / "nexara-dashboard.json"
ROWS = [
    "API Health",
    "Database",
    "Celery",
    "Infrastructure",
    "Real-time",
    "Activity",
    "Storage",
    "Security",
]


@pytest.fixture(scope="module")
def dash() -> dict:
    return json.loads(PATH.read_text())


def _panels(d: dict) -> list[dict]:
    return [p for p in d["panels"] if p["type"] not in ("row", "alertlist")]


def test_metadata(dash):
    assert dash["title"] == "Nexara System Dashboard"
    assert dash["description"] == "Complete overview of Nexara platform health and performance"
    assert dash["refresh"] == "30s"
    assert dash["time"]["from"] == "now-6h"
    assert dash["__inputs"][0]["pluginId"] == "prometheus"


def test_templating(dash):
    names = {v["name"] for v in dash["templating"]["list"]}
    assert {"datasource", "namespace", "community_id", "refresh_interval"} <= names


def test_rows(dash):
    titles = [p["title"] for p in dash["panels"] if p["type"] == "row"]
    assert titles == ROWS


def test_panels_have_title_description_queries(dash):
    panels = _panels(dash)
    assert len(panels) >= 30
    for p in panels:
        assert p["title"] and p["description"], p
        assert p["targets"], p["title"]
        for t in p["targets"]:
            assert t["expr"].strip()
            assert t["datasource"]["uid"] == "${datasource}"


def test_panel_types_and_unique_ids(dash):
    panels = dash["panels"]
    assert len({p["id"] for p in panels}) == len(panels)
    types = {p["type"] for p in panels}
    assert {"timeseries", "stat", "table", "heatmap", "gauge"} <= types


def test_stat_have_thresholds(dash):
    for p in _panels(dash):
        if p["type"] in ("stat", "gauge"):
            assert p["fieldConfig"]["defaults"]["thresholds"]["steps"], p["title"]


def test_uses_real_app_metrics(dash):
    exprs = " ".join(t["expr"] for p in _panels(dash) for t in p["targets"])
    for m in (
        "nexara_websocket_connections_active",
        "nexara_sse_connections_active",
        "nexara_users_online",
        "nexara_celery_queue_depth",
        "nexara_storage_used_bytes",
        "nexara_waf_blocks_total",
        "http_requests_total",
    ):
        assert m in exprs


def test_annotations_and_alerts(dash):
    assert dash["annotations"]["list"]
    assert any(p["type"] == "alertlist" for p in dash["panels"])


def test_no_unbalanced_brackets(dash):
    for p in _panels(dash):
        for t in p["targets"]:
            e = t["expr"]
            assert e.count("(") == e.count(")") and e.count("[") == e.count("]")


# --- review fixes (#134) -----------------------------------------------------

LIGHT_BG = "#ffffff"
DARK_BG = "#181b1f"  # Grafana dark panel background
HEX = re.compile(r"#[0-9A-Fa-f]{6}\b")
STATUS_SEL = re.compile(r'status\s*(?:=~|!~|!=|=)\s*"([^"]*)"')
SELECTOR = re.compile(r"\b(http_\w+|nexara_\w+)\{([^}]*)\}")


def _exprs(d: dict) -> list[str]:
    return [t["expr"] for p in _panels(d) for t in p["targets"]]


def _luminance(hex_color: str) -> float:
    rgb = [int(hex_color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _contrast(a: str, b: str) -> float:
    lo, hi = sorted((_luminance(a), _luminance(b)))
    return (hi + 0.05) / (lo + 0.05)


def test_status_selectors_match_grouped_codes(dash):
    """Instrumentator groups status codes (should_group_status_codes=True)."""
    for e in _exprs(dash):
        if "http_requests_total" not in e:
            continue
        for value in STATUS_SEL.findall(e):
            assert re.fullmatch(r"[1-5]xx(\|[1-5]xx)*", value), e


def test_status_selector_rejects_fine_codes():
    for bad in ('status="403"', 'status=~"401|403"', 'status=~"5.."'):
        (value,) = STATUS_SEL.findall(bad)
        assert not re.fullmatch(r"[1-5]xx(\|[1-5]xx)*", value)


def test_namespace_variable_is_used(dash):
    sels = [s for e in _exprs(dash) for s in SELECTOR.findall(e)]
    assert sels
    for metric, labels in sels:
        assert 'namespace=~"$namespace"' in labels, metric
    var = next(v for v in dash["templating"]["list"] if v["name"] == "namespace")
    assert var["includeAll"] and var["allValue"] == ".*"


def test_colors_reach_3_to_1_on_both_themes(dash):
    colors = set(HEX.findall(PATH.read_text()))
    assert colors
    for c in colors:
        for bg in (LIGHT_BG, DARK_BG):
            assert _contrast(c, bg) >= 3.0, (c, bg, round(_contrast(c, bg), 2))


def test_drilldown_links_target_own_panel(dash):
    for p in _panels(dash):
        for link in p.get("fieldConfig", {}).get("defaults", {}).get("links", []):
            url = link["url"]
            assert "${__panel}" not in url and "${__dashboard}" not in url
            assert url.startswith(f"/d/{dash['uid']}?")
            assert f"viewPanel={p['id']}&" in url


def test_panel_titles_match_queries(dash):
    by_title = {p["title"]: p for p in _panels(dash)}
    db = by_title["Query latency (mean)"]
    assert "pg_stat_statements_seconds_total" in db["targets"][0]["expr"]
    assert db["fieldConfig"]["defaults"]["unit"] == "ms"
    assert "Media uploaded (1h)" in by_title
    assert "Media uploads (1h)" not in by_title
    assert "403 errors" not in by_title
