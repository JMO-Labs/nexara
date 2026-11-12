"""
@file test_helm_hardening.py
@brief Helm chart: worker HPA, PDBs, NetworkPolicies, security contexts (nexara#142).
"""

import shutil
import subprocess
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

CHART = Path(__file__).resolve().parents[4] / "deploy" / "helm" / "nexara"

if shutil.which("helm") is None:
    pytest.skip("helm not installed", allow_module_level=True)


def _render(*sets: str) -> list[dict]:
    args = ["helm", "template", "nexara", str(CHART)]
    for s in sets:
        args += ["--set", s]
    res = subprocess.run(args, capture_output=True, text=True)
    assert res.returncode == 0, res.stdout + res.stderr
    return [d for d in yaml.safe_load_all(res.stdout) if d]


def _all(docs: list[dict], kind: str) -> dict[str, dict]:
    return {
        d["metadata"]["name"].removeprefix("nexara-nexara-"): d for d in docs if d["kind"] == kind
    }


def test_worker_hpa_targets_worker_deployment() -> None:
    hpas = _all(_render(), "HorizontalPodAutoscaler")
    assert set(hpas) == {"api", "worker"}
    api = hpas["api"]["spec"]
    assert api["scaleTargetRef"]["name"] == "nexara-nexara-api"
    assert api["metrics"][0]["resource"]["target"]["averageUtilization"] == 70
    w = hpas["worker"]["spec"]
    assert w["scaleTargetRef"] == {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "name": "nexara-nexara-worker",
    }
    assert w["minReplicas"] == 2 and w["maxReplicas"] == 8


def test_worker_hpa_disabled_keeps_static_replicas() -> None:
    docs = _render("hpa.worker.enabled=false")
    assert set(_all(docs, "HorizontalPodAutoscaler")) == {"api"}
    assert _all(docs, "Deployment")["worker"]["spec"]["replicas"] == 2
    assert "replicas" not in _all(_render(), "Deployment")["worker"]["spec"]


def test_pdb_for_api_and_worker() -> None:
    pdbs = _all(_render(), "PodDisruptionBudget")
    assert set(pdbs) == {"api", "worker"}
    for name, pdb in pdbs.items():
        assert pdb["spec"]["minAvailable"] == 1
        assert pdb["spec"]["selector"]["matchLabels"]["app.kubernetes.io/component"] == name
    assert not _all(_render("pdb.enabled=false"), "PodDisruptionBudget")


def test_networkpolicy_off_by_default() -> None:
    assert not _all(_render(), "NetworkPolicy")


def test_networkpolicies_restrict_paths() -> None:
    nps = _all(_render("networkPolicy.enabled=true"), "NetworkPolicy")
    assert {"api", "worker", "postgresql", "valkey"} <= set(nps)
    assert "ingress" in nps["api"]["spec"]
    assert "Ingress" not in nps["worker"]["spec"]["policyTypes"]

    def peers(np: dict, direction: str) -> set[str]:
        out = set()
        for rule in np["spec"].get(direction, []):
            for p in rule.get("from", []) + rule.get("to", []):
                sel = p.get("podSelector", {}).get("matchLabels", {})
                if "app.kubernetes.io/component" in sel:
                    out.add(sel["app.kubernetes.io/component"])
        return out

    assert {"postgresql", "valkey"} <= peers(nps["api"], "egress")
    assert {"postgresql", "valkey"} <= peers(nps["worker"], "egress")
    assert peers(nps["postgresql"], "ingress") == {"api", "worker", "beat"}
    assert peers(nps["valkey"], "ingress") == {"api", "worker", "beat"}


def test_networkpolicy_skips_disabled_internal_services() -> None:
    docs = _render(
        "networkPolicy.enabled=true",
        "postgresql.enabled=false",
        "postgresql.external.host=db",
        "postgresql.external.password=x",
        "valkey.enabled=false",
        "valkey.external.url=redis://c:6379",
    )
    assert set(_all(docs, "NetworkPolicy")) == {"api", "worker"}


def test_app_pods_have_hardened_security_context() -> None:
    deps = _all(_render(), "Deployment")
    for name in ("api", "worker", "beat"):
        pod = deps[name]["spec"]["template"]["spec"]
        assert pod["securityContext"]["runAsNonRoot"] is True
        assert pod["securityContext"]["runAsUser"] == 1000
        sc = pod["containers"][0]["securityContext"]
        assert sc["allowPrivilegeEscalation"] is False
    for name in ("worker", "beat"):
        c = deps[name]["spec"]["template"]["spec"]["containers"][0]
        assert c["securityContext"]["readOnlyRootFilesystem"] is True
        assert any(m["mountPath"] == "/tmp" for m in c["volumeMounts"])


def test_all_containers_have_requests_and_limits() -> None:
    for d in _render():
        if d["kind"] in ("Deployment", "StatefulSet"):
            for c in d["spec"]["template"]["spec"]["containers"]:
                assert c["resources"]["requests"] and c["resources"]["limits"], d["metadata"][
                    "name"
                ]
