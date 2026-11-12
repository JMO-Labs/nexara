"""
@file test_helm.py
@brief Validates the Helm chart: lint, template rendering and default values.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

CHART = Path(__file__).resolve().parents[4] / "deploy" / "helm" / "nexara"

if shutil.which("helm") is None:
    if os.environ.get("REQUIRE_HELM"):
        pytest.fail("helm is required (REQUIRE_HELM set)", pytrace=False)
    pytest.skip("helm not installed", allow_module_level=True)


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
        "postgresql.external.password=extpass",
        "valkey.enabled=false",
        "valkey.external.url=redis://cache:6379",
    )
    kinds = [d["kind"] for d in docs]
    assert "Ingress" in kinds
    assert len([k for k in kinds if k == "Deployment"]) == 3


def test_external_db_requires_password_or_secret() -> None:
    args = ["template", "nexara", str(CHART), "--set", "postgresql.enabled=false"]
    res = subprocess.run(["helm", *args], capture_output=True, text=True)
    assert res.returncode != 0
    assert "postgresql.external.password or postgresql.external.existingSecret" in res.stderr


def test_external_db_existing_secret_renders_without_password() -> None:
    docs = _render("postgresql.enabled=false", "postgresql.external.existingSecret=mydb")
    assert not any(d["kind"] == "Secret" and d["metadata"]["name"].endswith("-db") for d in docs)


def _secret_data(docs: list[dict], suffix: str) -> dict:
    return next(
        d["data"] for d in docs if d["kind"] == "Secret" and d["metadata"]["name"].endswith(suffix)
    )


def test_supplied_secrets_are_rendered() -> None:
    import base64

    docs = _render("postgresql.password=pgpass", "secrets.jwtSecret=jwtval")
    assert base64.b64decode(_secret_data(docs, "-db")["database-password"]) == b"pgpass"
    assert base64.b64decode(_secret_data(docs, "-app")["secret-key"]) == b"jwtval"


def test_secrets_use_lookup_and_keep_policy() -> None:
    text = (CHART / "templates" / "secrets.yaml").read_text()
    assert 'lookup "v1" "Secret"' in text
    assert "helm.sh/resource-policy" in text


def _worker(docs: list[dict]) -> dict:
    return next(
        d for d in docs if d["kind"] == "Deployment" and d["metadata"]["name"].endswith("-worker")
    )


def test_worker_mounts_media_when_local() -> None:
    pod = _worker(_render())["spec"]["template"]["spec"]
    assert any(m["mountPath"] == "/data/media" for m in pod["containers"][0]["volumeMounts"])
    assert pod["volumes"][0]["persistentVolumeClaim"]["claimName"].endswith("-media")


def test_worker_has_no_media_mount_for_s3() -> None:
    pod = _worker(_render("storage.backend=s3"))["spec"]["template"]["spec"]
    assert "volumes" not in pod


def test_media_pvc_access_modes_configurable() -> None:
    def modes(*sets: str) -> list[str]:
        pvc = next(d for d in _render(*sets) if d["kind"] == "PersistentVolumeClaim")
        return pvc["spec"]["accessModes"]

    assert modes() == ["ReadWriteMany"]
    assert modes("storage.local.accessModes={ReadWriteOnce}") == ["ReadWriteOnce"]
