"""@file test_contract_manifest.py
@brief Tests for contract_tests.manifest_tests and code_structure_tests.
"""

import json

from . import _contract as c
from contract_tests import code_structure_tests as st  # noqa: E402
from contract_tests import manifest_tests as mt  # noqa: E402


def _fails(checks):
    return {x.name for x in checks if x.status == "fail"}


def test_valid_manifest_passes(tmp_path):
    d = c.make(tmp_path, backend={"routes": "router.py"})
    assert _fails(mt.run(d)) == set()


def test_invalid_semver_fails(tmp_path):
    assert "manifest.version" in _fails(mt.run(c.make(tmp_path, version="1.0")))


def test_missing_required_field_fails(tmp_path):
    d = c.make(tmp_path)
    data = json.loads((d / "manifest.json").read_text())
    del data["author"]
    (d / "manifest.json").write_text(json.dumps(data))
    res = c.by_name(mt.run(d), "manifest.required_fields")
    assert res[0].status == "fail" and "author" in res[0].message


def test_unknown_permission_fails(tmp_path):
    assert "manifest.permissions" in _fails(mt.run(c.make(tmp_path, permissions=["teleport"])))


def test_duplicate_hook_fails(tmp_path):
    d = c.make(tmp_path, hooks={"after_post_created": "a", "on_after_post_created": "b"})
    assert "manifest.duplicate_hooks" in _fails(mt.run(d))


def test_duplicate_json_key_fails(tmp_path):
    d = c.make(tmp_path)
    (d / "manifest.json").write_text('{"id":"demo","id":"demo2"}')
    assert "manifest.duplicate_keys" in _fails(mt.run(d))


def test_missing_backend_path_fails(tmp_path):
    d = c.make(tmp_path, backend={"routes": "nope.py"})
    assert "manifest.backend_routes_path" in _fails(mt.run(d))


def test_path_escape_fails(tmp_path):
    d = c.make(tmp_path, backend={"routes": "../x.py"})
    assert "manifest.backend_routes_path" in _fails(mt.run(d))


def test_deprecated_field_warns(tmp_path):
    d = c.make(tmp_path, entry="router.py")
    res = c.by_name(mt.run(d), "manifest.deprecated_field")
    assert res and res[0].status == "warn"


def test_id_trailing_dash_warns(tmp_path):
    res = c.by_name(mt.run(c.make(tmp_path, id="demo-")), "manifest.id_suffix")
    assert res[0].status == "warn"


def test_no_manifest_fails(tmp_path):
    assert _fails(mt.run(tmp_path)) == {"manifest.found"}


def test_structure_requires_init(tmp_path):
    d = c.make(tmp_path, backend={"routes": "router.py"})
    (d / "__init__.py").unlink()
    assert "structure.backend_init" in _fails(st.run(d))


def test_structure_unwanted_and_warnings(tmp_path):
    d = c.make(tmp_path, backend={"routes": "router.py"})
    (d / "node_modules").mkdir()
    checks = st.run(d)
    assert "structure.unwanted_files" in _fails(checks)
    assert {x.name for x in checks if x.status == "warn"} == {"structure.readme", "structure.tests"}


def test_structure_frontend_only_when_slots(tmp_path):
    d = c.make(tmp_path, frontend={"slots": {"sidebar": "Widget"}})
    assert {"structure.frontend_index", "structure.frontend_components"} <= _fails(st.run(d))


def test_structure_no_frontend_checks_without_slots(tmp_path):
    assert not any(x.name.startswith("structure.frontend") for x in st.run(c.make(tmp_path)))
