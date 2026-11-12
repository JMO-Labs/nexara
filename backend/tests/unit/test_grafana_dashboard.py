"""
@file test_grafana_dashboard.py
@brief Structural validation of deploy/grafana/nexara-dashboard.json.
"""

import json
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
