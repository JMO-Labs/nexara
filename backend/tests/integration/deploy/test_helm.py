"""
@file test_helm.py
@brief Validates the Helm chart: lint, template rendering and default values.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

CHART = Path(__file__).resolve().parents[4] / "deploy" / "helm" / "nexara"

pytestmark = pytest.mark.skipif(shutil.which("helm") is None, reason="helm not installed")


def _helm(*args: str) -> str:
    res = subprocess.run(["helm", *args], capture_output=True, text=True)
    assert res.returncode == 0, res.stdout + res.stderr
    return res.stdout


def _render(*sets: str) -> list[dict]:
    args = ["template", "nexara", str(CHART)]
    for s in sets:
        args += ["--set", s]
    return [d for d in yaml.safe_load_all(_helm(*args)) if d]


def test_helm_lint_passes() -> None:
    _helm("lint", str(CHART))


def test_chart_metadata() -> None:
    meta = yaml.safe_load((CHART / "Chart.yaml").read_text())
    assert meta["name"] == "nexara"
    assert meta["apiVersion"] == "v1"
    assert meta["version"] == "1.0.0" and meta["appVersion"] == "1.0.0"
    assert meta["maintainers"]


def test_default_values() -> None:
    v = yaml.safe_load((CHART / "values.yaml").read_text())
    assert v["api"]["replicas"] == 3
    assert v["worker"]["replicas"] == 2
    assert v["beat"]["replicas"] == 1
    assert v["valkey"]["enabled"] is True
    assert v["postgresql"]["enabled"] is True
    assert v["ingress"]["enabled"] is False
    assert v["hpa"]["enabled"] is True
    assert v["hpa"]["targetCPUUtilization"] == 70


def test_default_template_renders_expected_kinds() -> None:
    kinds = {(d["kind"], d["metadata"]["name"]) for d in _render()}
    kinds_only = {k for k, _ in kinds}
    assert {"Deployment", "Secret", "ConfigMap", "Service", "HorizontalPodAutoscaler"} <= kinds_only
    assert "Ingress" not in kinds_only
    assert len([k for k, _ in kinds if k == "Deployment"]) >= 5  # api, worker, beat, valkey, pg


def test_ingress_and_external_services() -> None:
    docs = _render(
        "ingress.enabled=true",
        "postgresql.enabled=false",
        "postgresql.external.host=db.example.com",
        "valkey.enabled=false",
        "valkey.external.url=redis://cache:6379",
    )
    kinds = [d["kind"] for d in docs]
    assert "Ingress" in kinds
    assert len([k for k in kinds if k == "Deployment"]) == 3
