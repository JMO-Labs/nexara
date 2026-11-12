"""@file Tests for the cookiecutter-nexara-plugin scaffold.

@brief Renders the template with Jinja2 (same engine as cookiecutter), runs the
generation hooks, and checks the output against the manifest schema.
"""

import ast
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

import pytest
from jinja2 import Environment

from app.plugins.manifest import PluginPermission, load_manifest

BACKEND = Path(__file__).resolve().parents[3]
TEMPLATE = BACKEND.parent / "plugins" / "cookiecutter-nexara-plugin"
SLUG_RE = r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$"


def _defaults() -> dict[str, Any]:
    ctx = json.loads((TEMPLATE / "cookiecutter.json").read_text())
    ctx.update(plugin_id="my-awesome-plugin", plugin_name="My Awesome Plugin")
    return ctx


def _render(text: str, ctx: dict[str, Any]) -> str:
    return Environment(keep_trailing_newline=True).from_string(text).render(cookiecutter=ctx)


def _context(overrides: dict[str, Any]) -> dict[str, Any]:
    """@brief Apply overrides, then render derived (templated) defaults in order."""
    ctx: dict[str, Any] = {}
    for key, default in _defaults().items():
        value = overrides.get(key, default)
        ctx[key] = _render(value, ctx) if isinstance(value, str) and "{{" in value else value
    return ctx


def generate(out: Path, **overrides: Any) -> Path:
    """@brief Render the template into ``out`` and run pre/post hooks."""
    ctx = _context(overrides)
    project = out / ctx["plugin_id"]
    root = next(p for p in TEMPLATE.iterdir() if p.is_dir() and "cookiecutter" in p.name)
    hooks = TEMPLATE / "hooks"
    if (hooks / "pre_gen_project.py").exists():
        script = out / "_pre.py"
        script.write_text(_render((hooks / "pre_gen_project.py").read_text(), ctx))
        subprocess.run([sys.executable, str(script)], check=True, cwd=out)
    for src in [root, *root.rglob("*")]:
        dest = out / _render(str(src.relative_to(TEMPLATE)), ctx)
        if src.is_dir():
            dest.mkdir(parents=True, exist_ok=True)
        else:
            dest.write_text(_render(src.read_text(), ctx))
    if (hooks / "post_gen_project.py").exists():
        script = out / "_post.py"
        script.write_text(_render((hooks / "post_gen_project.py").read_text(), ctx))
        subprocess.run([sys.executable, str(script)], check=True, cwd=project)
    return project


class TestCookiecutterJson:
    def test_has_required_variables(self) -> None:
        ctx = json.loads((TEMPLATE / "cookiecutter.json").read_text())
        for key in (
            "plugin_id", "plugin_name", "author_name", "author_email", "description",
            "has_backend", "has_frontend", "backend_permissions", "min_core_version",
        ):  # fmt: skip
            assert key in ctx
        assert ctx["has_backend"] is True
        assert ctx["has_frontend"] is False
        assert ctx["min_core_version"] == "1.0.0"

    def test_default_permissions_are_valid_enum_values(self) -> None:
        perms = json.loads(
            json.loads((TEMPLATE / "cookiecutter.json").read_text())["backend_permissions"]
        )
        assert all(p in {e.value for e in PluginPermission} for p in perms)

    def test_pre_gen_allowed_matches_enum(self) -> None:
        tree = ast.parse((TEMPLATE / "hooks" / "pre_gen_project.py").read_text())
        node = next(
            n.value
            for n in ast.walk(tree)
            if isinstance(n, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "ALLOWED" for t in n.targets)
        )
        assert ast.literal_eval(node) == {p.value for p in PluginPermission}

    def test_sample_plugin_id_matches_slug(self) -> None:
        assert re.match(SLUG_RE, _defaults()["plugin_id"])


class TestGeneration:
    def test_manifest_parses(self, tmp_path: Path) -> None:
        project = generate(tmp_path, author_name="Jane", author_email="j@x.io")
        m = load_manifest(project)
        assert m.id == "my-awesome-plugin"
        assert m.name == "My Awesome Plugin"
        assert m.author == "Jane <j@x.io>"
        assert m.version == "0.1.0"
        assert m.hooks == {}
        assert m.backend.routes == "router.py"
        assert m.backend.tasks is None
        assert m.permissions == [PluginPermission.DB_READ]

    def test_tasks_declared_only_with_celery_permission(self, tmp_path: Path) -> None:
        project = generate(tmp_path, backend_permissions='["db_read", "celery_tasks"]')
        assert load_manifest(project).backend.tasks == "tasks.py"
        assert (project / "tasks.py").is_file()

    def test_quotes_in_text_fields_are_escaped(self, tmp_path: Path) -> None:
        project = generate(
            tmp_path,
            plugin_name='My "Best" Plugin',
            author_name='Jo "J"',
            description='a "b" \\ c',
        )
        m = load_manifest(project)
        assert (m.name, m.author) == ('My "Best" Plugin', 'Jo "J" <you@example.com>')
        assert m.description == 'a "b" \\ c'

    def test_no_celery_permission_drops_tasks_file(self, tmp_path: Path) -> None:
        assert not (generate(tmp_path) / "tasks.py").exists()

    def test_register_hooks_matches_loader_signature(self, tmp_path: Path) -> None:
        src = (generate(tmp_path) / "hooks.py").read_text()
        fn = next(
            n
            for n in ast.parse(src).body
            if isinstance(n, ast.FunctionDef) and n.name == "register_hooks"
        )
        assert [a.arg for a in fn.args.args] == ["community_id", "manifest"]
        assert "HookRegistry.register(" in src

    def test_structure_backend_only(self, tmp_path: Path) -> None:
        project = generate(tmp_path)
        for name in (
            "__init__.py", "router.py", "models.py", "hooks.py", "README.md",
            "requirements.txt", ".gitignore", "LICENSE", "manifest.toml",
            "tests/test_my_awesome_plugin.py", "pyproject.toml",
        ):  # fmt: skip
            assert (project / name).is_file(), name
        assert not (project / "frontend").exists()
        assert (project / "requirements.txt").read_text() == ""

    def test_frontend_files_when_enabled(self, tmp_path: Path) -> None:
        project = generate(tmp_path, has_frontend=True)
        for name in ("index.tsx", "components/Example.tsx", "hooks/useExample.ts"):
            assert (project / "frontend" / name).is_file(), name
        load_manifest(project)

    def test_no_backend_drops_backend_files(self, tmp_path: Path) -> None:
        project = generate(tmp_path, has_backend=False, has_frontend=True)
        assert not (project / "router.py").exists()
        assert not (project / "tasks.py").exists()
        assert load_manifest(project).backend.routes is None

    def test_multiple_permissions(self, tmp_path: Path) -> None:
        project = generate(tmp_path, backend_permissions='["db_read", "db_write"]')
        assert len(load_manifest(project).permissions) == 2

    def test_every_permission_accepted(self, tmp_path: Path) -> None:
        perms = [p.value for p in PluginPermission]
        project = generate(tmp_path, backend_permissions=json.dumps(perms))
        assert load_manifest(project).permissions == list(PluginPermission)

    def test_license_and_readme(self, tmp_path: Path) -> None:
        project = generate(tmp_path, author_name="Jane")
        assert "Jane" in (project / "LICENSE").read_text()
        readme = (project / "README.md").read_text()
        for heading in ("Installation", "Development", "Testing", "Contributing"):
            assert heading in readme
        assert "My Awesome Plugin" in readme

    @pytest.mark.parametrize("bad", ["Bad_Id", "-lead", "trail-", "UPPER", "a b"])
    def test_invalid_plugin_id_rejected(self, tmp_path: Path, bad: str) -> None:
        with pytest.raises(subprocess.CalledProcessError):
            generate(tmp_path, plugin_id=bad)

    def test_invalid_permission_rejected(self, tmp_path: Path) -> None:
        with pytest.raises(subprocess.CalledProcessError):
            generate(tmp_path, backend_permissions='["root_access"]')

    def test_plugin_module_derived_from_id(self) -> None:
        assert _context({})["__plugin_module"] == "my_awesome_plugin"

    def test_ruff_rules_match_backend(self, tmp_path: Path) -> None:
        project = generate(tmp_path)
        plugin = tomllib.loads((project / "pyproject.toml").read_text())
        core = tomllib.loads((BACKEND / "pyproject.toml").read_text())
        assert plugin["tool"]["ruff"]["lint"]["select"] == core["tool"]["ruff"]["lint"]["select"]

    @pytest.mark.parametrize("frontend", [False, True])
    def test_generated_python_passes_ruff(self, tmp_path: Path, frontend: bool) -> None:
        pytest.importorskip("ruff")
        project = generate(tmp_path, has_frontend=frontend)
        res = subprocess.run(
            [sys.executable, "-m", "ruff", "check", "."],
            capture_output=True, text=True, cwd=project,
        )  # fmt: skip
        assert res.returncode == 0, res.stdout

    def test_generated_python_passes_mypy(self, tmp_path: Path) -> None:
        pytest.importorskip("mypy")
        project = generate(tmp_path, has_frontend=True)
        res = subprocess.run(
            [sys.executable, "-m", "mypy", "--strict", "."],
            capture_output=True, text=True, cwd=project,
        )  # fmt: skip
        assert res.returncode == 0, res.stdout + res.stderr
