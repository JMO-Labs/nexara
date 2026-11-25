"""
@file
@brief Dependency install tests: lockfile/requirements validation, argv, runner.
"""

import json
import logging
from pathlib import Path
from typing import Any

import pytest

from host import deps
from host.deps import check_lockfile, install_deps, run_subprocess
from host.installer import InstallError
from host.models import InstallSpec
from tests.conftest import good_tar, spec_body

REG = "https://registry.npmjs.org/"
INTEGRITY = "sha512-" + "A" * 86 + "=="

Calls = list[tuple[list[str], Path, int | None]]


@pytest.fixture
def calls() -> Calls:
    return []


seen_reqs: list[str] = []


@pytest.fixture
def runner(calls: Calls) -> Any:
    seen_reqs.clear()

    async def run(argv: list[str], cwd: Path, uid: int | None) -> None:
        calls.append((argv, cwd, uid))
        if "-r" in argv:
            seen_reqs.append(Path(argv[argv.index("-r") + 1]).read_text())

    return run


def lock(packages: dict[str, Any], version: int = 3) -> dict[str, Any]:
    return {"name": "p", "lockfileVersion": version, "packages": {"": {"name": "p"}, **packages}}


def pkg(name: str = "left-pad", **over: Any) -> dict[str, Any]:
    entry = {
        "version": "1.3.0",
        "resolved": f"{REG}{name}/-/{name}-1.3.0.tgz",
        "integrity": INTEGRITY,
    }
    entry.update(over)
    return entry


def write_node(root: Path, lockdata: dict[str, Any], pj: dict[str, Any] | None = None) -> None:
    (root / "package.json").write_text(json.dumps(pj or {"dependencies": {"left-pad": "^1.3.0"}}))
    (root / "package-lock.json").write_text(json.dumps(lockdata))


def lock_code(root: Path) -> str:
    with pytest.raises(InstallError) as e:
        check_lockfile(root)
    return e.value.code


def test_lockfile_ok(tmp_path: Path) -> None:
    write_node(
        tmp_path,
        lock(
            {
                "node_modules/left-pad": pkg(),
                "node_modules/@s/x": pkg("@s/x"),
                "node_modules/a/node_modules/b": pkg("b"),
            }
        ),
    )
    check_lockfile(tmp_path)


@pytest.mark.parametrize(
    "entry",
    [
        pkg(resolved="git+https://github.com/x/y.git#abc"),
        pkg(resolved="file:../../etc"),
        pkg(resolved="http://registry.npmjs.org/left-pad/-/left-pad-1.3.0.tgz"),
        pkg(resolved="https://evil.example/left-pad.tgz"),
        pkg(resolved="https://registry.npmjs.org.evil.example/x.tgz"),
        {"resolved": "../x", "link": True},
        pkg(integrity=None),
        {"version": "1.0.0"},
    ],
    ids=["git", "file", "http", "other-host", "lookalike", "link", "no-integrity", "no-resolved"],
)
def test_lockfile_unsafe_entries(tmp_path: Path, entry: dict[str, Any]) -> None:
    entry = {k: v for k, v in entry.items() if v is not None}
    write_node(tmp_path, lock({"node_modules/left-pad": entry}))
    assert lock_code(tmp_path) == "lockfile_unsafe"


@pytest.mark.parametrize(
    "key", ["node_modules/../../x", "lib/x", "node_modules/a/../../b", "node_modules/"]
)
def test_lockfile_bad_paths(tmp_path: Path, key: str) -> None:
    write_node(tmp_path, lock({key: pkg()}))
    assert lock_code(tmp_path) == "lockfile_unsafe"


def test_lockfile_v1_rejected(tmp_path: Path) -> None:
    write_node(tmp_path, {"lockfileVersion": 1, "dependencies": {}})
    assert lock_code(tmp_path) == "lockfile_unsafe"


def test_lockfile_missing(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text("{}")
    assert lock_code(tmp_path) == "lockfile_unsafe"


def test_lockfile_garbage(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text("{}")
    (tmp_path / "package-lock.json").write_text("{nope")
    assert lock_code(tmp_path) == "lockfile_unsafe"


@pytest.mark.parametrize(
    "spec",
    [
        "git+https://github.com/x/y",
        "file:../x",
        "link:../x",
        "workspace:*",
        "user/repo",
        "https://x.example/y.tgz",
        "npm:other@1",
    ],
)
def test_package_json_unsafe_specs(tmp_path: Path, spec: str) -> None:
    write_node(tmp_path, lock({}), {"dependencies": {"x": spec}})
    assert lock_code(tmp_path) == "lockfile_unsafe"


def test_lockfile_uppercase_legacy_name_ok(tmp_path: Path) -> None:
    write_node(tmp_path, lock({"node_modules/JSONStream": pkg("JSONStream")}))
    check_lockfile(tmp_path)


@pytest.mark.parametrize(
    "packages",
    [
        {
            "node_modules/a": pkg("a"),
            "node_modules/a/node_modules/b": {"version": "1.0.0", "inBundle": True},
        },
        {"node_modules/a": pkg("a"), "node_modules/a/node_modules/b": pkg("b", inBundle=True)},
        {"node_modules/b": {"version": "1.3.0", "inBundle": True}},
        {"node_modules/b": {"version": "http://127.0.0.1/x.tgz", "inBundle": True}},
    ],
    ids=["verified-parent", "with-resolved", "root-parent", "url-version"],
)
def test_inbundle_rejected(tmp_path: Path, packages: dict[str, Any]) -> None:
    write_node(tmp_path, lock(packages))
    assert lock_code(tmp_path) == "lockfile_unsafe"


@pytest.mark.parametrize("field", ["bundleDependencies", "bundledDependencies"])
def test_bundle_dependencies_rejected(tmp_path: Path, field: str) -> None:
    write_node(tmp_path, lock({}), {field: ["left-pad"]})
    assert lock_code(tmp_path) == "lockfile_unsafe"
    lk = lock({})
    lk["packages"][""][field] = ["left-pad"]
    write_node(tmp_path, lk)
    assert lock_code(tmp_path) == "lockfile_unsafe"


@pytest.mark.parametrize(
    "overrides",
    [
        {"left-pad": "http://127.0.0.1/x.tgz"},
        {"a": {"b": "git+https://x/y"}},
        {"a": "$left-pad"},
        {"a": ["1.0.0"]},
    ],
)
def test_unsafe_overrides_rejected(tmp_path: Path, overrides: dict[str, Any]) -> None:
    write_node(tmp_path, lock({}), {"overrides": overrides})
    assert lock_code(tmp_path) == "lockfile_unsafe"


def test_safe_overrides_ok(tmp_path: Path) -> None:
    write_node(tmp_path, lock({}), {"overrides": {"a": "1.2.3", "b": {".": "^2", "c": "~1"}}})
    check_lockfile(tmp_path)


def test_package_json_workspaces_rejected(tmp_path: Path) -> None:
    write_node(tmp_path, lock({}), {"workspaces": ["a"]})
    assert lock_code(tmp_path) == "lockfile_unsafe"


def mkspec(runtime: str = "python") -> InstallSpec:
    return InstallSpec.model_validate(spec_body(good_tar(), runtime=runtime))


async def test_python_argv(tmp_path: Path, runner: Any, calls: Calls) -> None:
    root = tmp_path / "plugins" / "p" / "1.0.0"
    root.mkdir(parents=True)
    (root / "requirements.txt").write_text("httpx==0.28.1\n")
    await install_deps(mkspec(), root, runner, uid=20001)
    (venv, _, uid), (pip, cwd, _) = calls
    assert venv[:2] == ["uv", "venv"] and "--no-config" in venv
    assert venv[venv.index("--python") + 1] == deps.PLUGIN_PYTHON
    assert pip[:3] == ["uv", "pip", "install"]
    for flag in ("--no-config", "--no-sources"):
        assert flag in pip
    assert pip[pip.index("--only-binary") + 1] == ":all:"
    assert pip[pip.index("--index-url") + 1] == "https://pypi.org/simple"
    assert cwd == root and uid == 20001
    assert "requirements.txt" not in pip and "--require-hashes" not in pip
    req = Path(pip[pip.index("-r") + 1])
    assert req.is_absolute() and root not in req.parents
    assert req.parent.parent == root.parent / ".cache"
    assert seen_reqs == ["httpx==0.28.1\n"]
    assert not req.exists() and not req.parent.exists()  # temp dir removed


H = "a" * 64


async def test_hashed_requirements_require_hashes(
    tmp_path: Path, runner: Any, calls: Calls
) -> None:
    root = tmp_path / "plugins" / "p" / "1.0.0"
    root.mkdir(parents=True)
    (root / "requirements.txt").write_text(f"httpx==0.28.1 --hash=sha256:{H}\n")
    await install_deps(mkspec(), root, runner)
    assert "--require-hashes" in calls[1][0]


async def test_canonical_file_ignores_planted_symlink(
    tmp_path: Path, runner: Any, calls: Calls
) -> None:
    root = tmp_path / "plugins" / "p" / "1.0.0"
    root.mkdir(parents=True)
    (root / "requirements.txt").write_text("httpx==0.28.1\n")
    victim = tmp_path / "victim"
    victim.write_text("keep")
    cache = root.parent / ".cache"
    cache.mkdir()
    (cache / deps.CANONICAL_REQS).symlink_to(victim)
    await install_deps(mkspec(), root, runner)
    assert victim.read_text() == "keep"
    assert seen_reqs == ["httpx==0.28.1\n"]


@pytest.mark.parametrize("runtime", ["python", "node"])
async def test_symlinked_cache_refused(
    tmp_path: Path, runner: Any, calls: Calls, runtime: str
) -> None:
    root = tmp_path / "plugins" / "p" / "1.0.0"
    root.mkdir(parents=True)
    (root / "requirements.txt").write_text("httpx==0.28.1\n")
    write_node(root, lock({"node_modules/left-pad": pkg()}))
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (root.parent / ".cache").symlink_to(elsewhere)
    with pytest.raises(InstallError) as e:
        await install_deps(mkspec(runtime), root, runner)
    assert e.value.code == "unsafe_cache"
    assert calls == [] and list(elsewhere.iterdir()) == []


async def test_symlinked_plugin_dir_refused(tmp_path: Path, runner: Any, calls: Calls) -> None:
    real = tmp_path / "real"
    (real / "1.0.0").mkdir(parents=True)
    (real / "1.0.0" / "requirements.txt").write_text("httpx==0.28.1\n")
    (tmp_path / "plugins").mkdir()
    (tmp_path / "plugins" / "p").symlink_to(real)
    with pytest.raises(InstallError) as e:
        await install_deps(mkspec(), tmp_path / "plugins" / "p" / "1.0.0", runner)
    assert e.value.code == "unsafe_cache"
    assert calls == []


async def test_python_bad_requirements_never_runs_pip(
    tmp_path: Path, runner: Any, calls: Calls
) -> None:
    (tmp_path / "requirements.txt").write_text("-r /etc/passwd\n")
    with pytest.raises(InstallError):
        await install_deps(mkspec(), tmp_path, runner)
    assert calls == []


async def test_node_argv(tmp_path: Path, runner: Any, calls: Calls) -> None:
    root = tmp_path / "plugins" / "p" / "1.0.0"
    root.mkdir(parents=True)
    write_node(root, lock({"node_modules/left-pad": pkg()}))
    await install_deps(mkspec("node"), root, runner)
    argv = calls[0][0]
    assert argv[:2] == ["npm", "ci"]
    for flag in (
        "--omit=dev",
        "--ignore-scripts",
        "--userconfig=/dev/null",
        "--globalconfig=/nonexistent/npmrc",
        f"--registry={REG}",
        "--git=/bin/false",
    ):
        assert flag in argv
    assert f"--cache={tmp_path / 'plugins' / 'p' / '.cache' / 'npm'}" in argv


async def test_node_unsafe_lock_never_runs_npm(tmp_path: Path, runner: Any, calls: Calls) -> None:
    write_node(tmp_path, lock({"node_modules/x": pkg(resolved="git+https://x/y")}))
    with pytest.raises(InstallError):
        await install_deps(mkspec("node"), tmp_path, runner)
    assert calls == []


async def test_run_subprocess_env_and_no_output_logged(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PLUGIN_HOST_SECRET", "host-SECRET-xyz")
    monkeypatch.setenv("npm_config_registry", "http://evil")
    root = tmp_path / "plugins" / "p" / "1.0.0"
    root.mkdir(parents=True)
    caplog.set_level(logging.DEBUG)
    script = 'env > envdump; echo "LEAK $PLUGIN_HOST_SECRET out"; echo LEAK-ERR >&2; exit 3'
    with pytest.raises(InstallError) as e:
        await run_subprocess(["sh", "-c", script], root, None)
    assert e.value.code == "deps_failed:exit=3"
    assert "LEAK" not in caplog.text
    env = (root / "envdump").read_text()
    assert "host-SECRET-xyz" not in env and "npm_config" not in env
    assert f"HOME={tmp_path / 'plugins' / 'p' / '.cache'}" in env
    assert "UV_NO_CONFIG=1" in env
