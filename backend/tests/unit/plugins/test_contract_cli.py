"""@file test_contract_cli.py
@brief Tests for contract_tester CLI, reporting and integration checks.
"""

import json

import contract_tester as ct  # noqa: E402
from contract_tests import integration_tests as it  # noqa: E402
from contract_tests import reporting  # noqa: E402
from contract_tests.common import fail, ok, warn  # noqa: E402

from . import _contract as c


def test_example_plugins_exit_ok_or_warnings():
    for name in ("example-recipe-box", "example-trivia"):
        assert ct.main([str(c.PLUGINS / name)]) in (0, 2), name


def test_broken_fixtures_exit_1():
    for name in ("broken-manifest", "broken-security"):
        assert ct.main([str(c.FIXTURES / name), "--format", "json"]) == 1, name


def test_exit_codes_and_strict():
    assert ct.exit_code([ok("a")]) == 0
    assert ct.exit_code([ok("a"), warn("b", "m")]) == 2
    assert ct.exit_code([ok("a"), warn("b", "m")], strict=True) == 1
    assert ct.exit_code([fail("c", "m")]) == 1


def test_test_flag_repeatable(capsys):
    ct.main(
        [
            str(c.FIXTURES / "broken-manifest"),
            "--test",
            "manifest",
            "--test",
            "security",
            "--format",
            "json",
        ]
    )
    names = {x["name"].split(".")[0] for x in json.loads(capsys.readouterr().out)["checks"]}
    assert names <= {"manifest", "security"}


def test_json_shape():
    d = reporting.to_dict([ok("a"), warn("b", "w"), fail("c", "f")])
    assert (d["passed"], d["failed"], d["warnings"]) == (1, 1, 1)
    assert d["checks"][2] == {"name": "c", "status": "fail", "message": "f"}


def test_text_markers_and_docs_link():
    text = reporting.to_text([ok("a"), warn("b.x", "w"), fail("c", "f")])
    assert "✓ a" in text and "✗ c: f" in text and "! b.x: w" in text
    assert text.count("see https://") == 2


def test_integration_missing_router_fails(tmp_path):
    d = c.make(tmp_path, code="x = 1\n", backend={"routes": "router.py"})
    assert c.by_name(it.run(d), "integration.router")[0].status == "fail"


def test_integration_valid_router_passes(tmp_path):
    ok_dir = c.make(
        tmp_path,
        code="from fastapi import APIRouter\nrouter = APIRouter()\n",
        backend={"routes": "router.py"},
    )
    assert c.by_name(it.run(ok_dir), "integration.router")[0].status == "pass"


def test_integration_import_error_fails(tmp_path):
    bad = c.make(tmp_path, code="raise RuntimeError\n", backend={"routes": "router.py"})
    assert c.by_name(it.run(bad), "integration.import_routes")[0].status == "fail"


def test_integration_hooks_signature(tmp_path):
    d = c.make(
        tmp_path,
        code="from fastapi import APIRouter\nrouter = APIRouter()\n",
        backend={"routes": "router.py"},
    )
    (d / "hooks.py").write_text("def register_hooks(a): ...\n")
    (d / "router.py").write_text(
        "from fastapi import APIRouter\nfrom .hooks import register_hooks\nrouter = APIRouter()\n"
    )
    assert c.by_name(it.run(d), "integration.register_hooks")[0].status == "fail"


_ROUTER = "from fastapi import APIRouter\nrouter = APIRouter()\n"


def _tasks_plugin(tmp_path, tasks_code, pid="demo"):
    d = c.make(tmp_path, code=_ROUTER, id=pid, backend={"routes": "router.py", "tasks": "tasks.py"})
    (d / "tasks.py").write_text(tasks_code)
    return d


def test_integration_celery_task_registered_passes(tmp_path):
    d = _tasks_plugin(
        tmp_path,
        "from app.tasks.celery_app import celery_app\n"
        "@celery_app.task(name='demo.contract_probe')\n"
        "def probe():\n    return 1\n",
    )
    assert c.by_name(it.run(d), "integration.celery_tasks")[0].status == "pass"


def test_integration_celery_no_tasks_fails(tmp_path):
    d = _tasks_plugin(tmp_path, "x = 1\n", pid="notasks")
    assert c.by_name(it.run(d), "integration.celery_tasks")[0].status == "fail"


def test_integration_hooks_valid_signature_passes(tmp_path):
    d = c.make(tmp_path, code=_ROUTER, backend={"routes": "router.py"})
    (d / "hooks.py").write_text("def register_hooks(community_id, manifest): ...\n")
    (d / "router.py").write_text(
        "from fastapi import APIRouter\nfrom .hooks import register_hooks\nrouter = APIRouter()\n"
    )
    assert c.by_name(it.run(d), "integration.register_hooks")[0].status == "pass"
