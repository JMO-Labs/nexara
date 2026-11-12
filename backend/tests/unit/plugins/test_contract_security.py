"""@file test_contract_security.py
@brief Tests for contract_tests.security_tests and permission_tests.
"""

import pytest

from . import _contract as c
from contract_tests import permission_tests as pt  # noqa: E402
from contract_tests import security_tests as sec  # noqa: E402


def _status(checks, name):
    return {x.status for x in checks if x.name == name}


@pytest.mark.parametrize(
    "line",
    [
        "from app.api.v1 import events",
        "import app.services.event_service",
        "from app.repositories.event_repo import EventRepo",
        "from app.models.post import Post",
        "from app.models import post",
    ],
)
def test_forbidden_imports_fail(tmp_path, line):
    d = c.make(tmp_path, code=line + "\n")
    assert "fail" in _status(sec.run(d), "security.forbidden_import")


@pytest.mark.parametrize(
    "line",
    [
        "from app.models.user import User",
        "from app.models.plugin import Plugin",
        "from app.models import user",
        "from app.plugins.context import PluginContext",
        "from app.core.dependencies import get_db",
        "from app.tasks.celery_app import celery_app",
        "from . import store",
    ],
)
def test_allowlisted_imports_pass(tmp_path, line):
    checks = sec.run(c.make(tmp_path, code=line + "\n"))
    assert not [x for x in checks if x.status != "pass"]


def test_nested_import_detected(tmp_path):
    d = c.make(tmp_path, code="def f():\n    from app.services import x\n")
    assert "fail" in _status(sec.run(d), "security.forbidden_import")


@pytest.mark.parametrize(
    "line",
    ['API_KEY = "abcd1234efgh5678"', 'x = "AKIAABCDEFGHIJKLMNOP"', 'password = "hunter2hunter2"'],
)
def test_hardcoded_secret_fails(tmp_path, line):
    assert "fail" in _status(sec.run(c.make(tmp_path, code=line + "\n")), "security.hardcoded_secret")


def test_secret_in_comment_or_short_value_ignored(tmp_path):
    d = c.make(tmp_path, code='# token = "abcdefghijkl"\ntoken = "x"\n')
    assert "security.hardcoded_secret" not in {x.name for x in sec.run(d)}


def test_http_without_timeout_warns_and_with_passes(tmp_path):
    d = c.make(tmp_path, code="import requests\nrequests.get('u')\nrequests.post('u', timeout=3)\n")
    res = [x for x in sec.run(d) if x.name == "security.http_timeout"]
    assert len(res) == 1 and res[0].status == "warn"


def test_used_but_undeclared_fails(tmp_path):
    code = "import requests\nasync def f(ctx):\n    await ctx.notify(1, 's', {})\n    ctx.db\n"
    checks = pt.run(c.make(tmp_path, code=code))
    for key in ("external_http", "send_notifications", "db"):
        assert "fail" in _status(checks, f"permissions.{key}")


def test_declared_but_unused_warns(tmp_path):
    d = c.make(tmp_path, permissions=["db_read", "send_notifications"], code="x = 1\n")
    checks = pt.run(d)
    assert "warn" in _status(checks, "permissions.db")
    assert "warn" in _status(checks, "permissions.send_notifications")


def test_logging_never_flagged(tmp_path):
    d = c.make(tmp_path, code="import logging\nlogging.getLogger('x').info('hi')\n")
    assert not [x for x in pt.run(d) if x.status != "pass"]


def test_declared_and_used_passes(tmp_path):
    code = (
        "from app.tasks.celery_app import celery_app\n"
        "@celery_app.task(name='x')\n"
        "def t(): ...\n"
        "async def f(ctx):\n    await ctx.db.get('k')\n"
    )
    d = c.make(tmp_path, permissions=["db_read", "celery_tasks"], code=code)
    assert not [x for x in pt.run(d) if x.status != "pass"]
