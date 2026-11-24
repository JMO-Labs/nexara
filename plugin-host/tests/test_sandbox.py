"""
@file
@brief bwrap argv / env / uid allocation unit tests, plus real-bwrap integration
       tests (marker `sandbox`; they need bwrap and the image's /plugin + /state mountpoints).
"""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from host import sandbox
from host.models import PluginEnv
from host.sandbox import bwrap_argv, install_argv, plugin_env, plugin_uid

PID = "dev.nexara.echo"
OTHER = "dev.nexara.other"
BIND_OPTS = {"--bind", "--ro-bind", "--dev-bind", "--bind-try", "--ro-bind-try", "--dev-bind-try"}


def _dirs(data: Path, pid: str = PID) -> tuple[Path, Path]:
    root = data / "plugins" / pid / "1.0.0"
    state = data / "plugin-state" / pid
    root.mkdir(parents=True)
    state.mkdir(parents=True)
    return root, state


def _binds(argv: list[str]) -> list[tuple[str, str]]:
    """@brief (source, dest) of every bind op before the `--` separator."""
    head = argv[: argv.index("--")]
    return [(head[i + 1], head[i + 2]) for i, a in enumerate(head) if a in BIND_OPTS]


def test_argv_layout(tmp_path: Path) -> None:
    root, state = _dirs(tmp_path)
    argv = bwrap_argv(PID, 20000, root, state, "node", "index.js", data_dir=tmp_path)
    assert argv[0] == "bwrap"
    joined = " ".join(argv)
    order = [
        "--ro-bind / /",
        "--tmpfs /tmp",
        f"--tmpfs {tmp_path}",
        f"--ro-bind {root} /plugin",
        f"--bind {state} /state",
        "--proc /proc",
        "--dev /dev",
    ]
    idx = [joined.index(o) for o in order]
    assert idx == sorted(idx)
    for flag in ("--unshare-pid", "--unshare-ipc", "--die-with-parent", "--new-session"):
        assert flag in argv
    assert argv[argv.index("--chdir") + 1] == "/plugin"
    assert argv[argv.index("--") :] == ["--", "node", "index.js"]


def test_argv_python_uses_venv_interpreter(tmp_path: Path) -> None:
    root, state = _dirs(tmp_path)
    argv = bwrap_argv(PID, 20000, root, state, "python", "echo.py", data_dir=tmp_path)
    assert argv[argv.index("--") :] == ["--", "/plugin/.venv/bin/python", "-u", "echo.py"]


def test_argv_never_binds_other_plugin(tmp_path: Path) -> None:
    root, state = _dirs(tmp_path)
    _dirs(tmp_path, OTHER)
    argv = bwrap_argv(PID, 20000, root, state, "node", "index.js", data_dir=tmp_path)
    sources = {s for s, _ in _binds(argv)}
    assert sources == {"/", str(root), str(state)}
    assert not any(OTHER in a for a in argv)


@pytest.mark.parametrize(
    "root_of,state_of", [(OTHER, PID), (PID, OTHER), (f"{PID}/../{OTHER}", PID)]
)
def test_argv_rejects_foreign_dirs(tmp_path: Path, root_of: str, state_of: str) -> None:
    _dirs(tmp_path)
    _dirs(tmp_path, OTHER)
    root = tmp_path / "plugins" / root_of / "1.0.0"
    state = tmp_path / "plugin-state" / state_of
    with pytest.raises(ValueError):
        bwrap_argv(PID, 20000, root, state, "node", "index.js", data_dir=tmp_path)


def test_argv_rejects_symlinked_root(tmp_path: Path) -> None:
    _, state = _dirs(tmp_path)
    other, _ = _dirs(tmp_path, OTHER)
    link = tmp_path / "plugins" / PID / "2.0.0"
    link.symlink_to(other)
    with pytest.raises(ValueError):
        bwrap_argv(PID, 20000, link, state, "node", "index.js", data_dir=tmp_path)


def test_runtime_argv_code_and_cache_read_only(tmp_path: Path) -> None:
    root, state = _dirs(tmp_path)
    (root.parent / ".cache").mkdir()
    argv = bwrap_argv(PID, 20000, root, state, "python", "echo.py", data_dir=tmp_path)
    head = argv[: argv.index("--")]
    writable = [head[i + 1] for i, a in enumerate(head) if a in {"--bind", "--dev-bind"}]
    assert writable == [str(state)]
    assert not any(".cache" in a for a in argv)
    assert ("--ro-bind", str(root), "/plugin") == tuple(head[head.index(str(root)) - 1 :][:3])


@pytest.mark.parametrize(
    "mode,want", [(0o644, 0o640), (0o600, 0o640), (0o755, 0o750), (0o4777, 0o750), (0o2700, 0o750)]
)
def test_sealed_mode_never_group_or_other_writable(mode: int, want: int) -> None:
    assert sandbox.sealed_mode(mode) == want


def _env() -> PluginEnv:
    return PluginEnv(
        NEXARA_TOKEN="tok",
        NEXARA_WEBHOOK_SECRET="whs",
        NEXARA_SETTINGS={"a": 1},  # type: ignore[arg-type]
    )


def test_plugin_env_is_exact(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PLUGIN_HOST_SECRET", "host-secret")
    monkeypatch.setenv("NEXARA_URL", "http://nexara:8080")
    env = plugin_env(_env(), 9100)
    assert env == {
        "NEXARA_URL": "http://nexara:8080",
        "NEXARA_TOKEN": "tok",
        "NEXARA_WEBHOOK_SECRET": "whs",
        "NEXARA_SETTINGS": '{"a": 1}',
        "NEXARA_COMMUNITIES": "[]",
        "NEXARA_DATA_DIR": "/state",
        "PORT": "9100",
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "HOME": "/tmp",
    }


def test_plugin_env_prefers_pushed_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEXARA_URL", "http://host-side")
    e = _env()
    e.NEXARA_URL = "http://pushed"
    assert plugin_env(e, 9100)["NEXARA_URL"] == "http://pushed"
    monkeypatch.delenv("NEXARA_URL")
    assert "NEXARA_URL" not in plugin_env(_env(), 9100)


def test_uid_is_stable_and_persisted(tmp_path: Path) -> None:
    assert plugin_uid(tmp_path, PID) == 20000
    assert plugin_uid(tmp_path, OTHER) == 20001
    assert plugin_uid(tmp_path, PID) == 20000
    assert json.loads((tmp_path / "uids.json").read_text()) == {PID: 0, OTHER: 1}
    (tmp_path / "uids.json").write_text(json.dumps({OTHER: 1}))
    assert plugin_uid(tmp_path, "dev.nexara.third") == 20002


def test_install_argv_binds_only_version_and_cache(tmp_path: Path) -> None:
    root, _ = _dirs(tmp_path)
    _dirs(tmp_path, OTHER)
    cache = root.parent / ".cache"
    argv = install_argv(["npm", "ci"], root, 20000, tmp_path)
    assert set(_binds(argv)) == {("/", "/"), (str(root), str(root)), (str(cache), str(cache))}
    head = argv[: argv.index("--")]
    writable = {head[i + 1] for i, a in enumerate(head) if a in {"--bind", "--dev-bind"}}
    assert writable == {str(root), str(cache)}  # only the version being installed + cache
    assert f"--tmpfs {tmp_path}" in " ".join(argv)
    assert argv[argv.index("--chdir") + 1] == str(root)
    assert argv[argv.index("--") :] == ["--", "npm", "ci"]
    with pytest.raises(ValueError):
        install_argv(["npm", "ci"], tmp_path / "plugins", 20000, tmp_path)


def test_self_test_fails_without_bwrap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sandbox, "BWRAP", "/nonexistent/bwrap")
    assert sandbox.self_test() is False


def test_self_test_requires_mountpoints(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(sandbox, "MOUNTPOINTS", (tmp_path / "missing",))
    assert sandbox.self_test() is False


def test_chown_tree_skips_when_not_root(tmp_path: Path) -> None:
    (tmp_path / "f").write_text("x")
    sandbox.chown_tree(tmp_path, 20000)  # non-root: no-op, must not raise
    if os.geteuid() != 0:
        assert (tmp_path / "f").stat().st_uid == os.geteuid()


# --- integration: real bwrap, image only -------------------------------------------------

_CAN_SANDBOX = shutil.which("bwrap") is not None and all(p.is_dir() for p in sandbox.MOUNTPOINTS)
needs_sandbox = pytest.mark.skipif(not _CAN_SANDBOX, reason="needs bwrap + /plugin,/state")

NODE_PROBE = b"""
const fs = require('fs');
const out = [];
try { fs.readFileSync(process.argv[2]); out.push('read-other'); }
catch (e) { out.push('no-other'); }
try { fs.readdirSync(process.argv[3]); out.push('list-data'); }
catch (e) { out.push('no-data'); }
fs.writeFileSync('/state/ok', 'w'); out.push('wrote-state');
try { fs.writeFileSync('/plugin/x', 'w'); out.push('wrote-code'); }
catch (e) { out.push('ro-code'); }
out.push(process.env.PLUGIN_HOST_SECRET ? 'leak' : 'no-leak');
console.log(out.join(','));
"""


@pytest.mark.sandbox
@needs_sandbox
@pytest.mark.skipif(shutil.which("node") is None, reason="needs node")
def test_node_plugin_isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root, state = _dirs(tmp_path)
    other, _ = _dirs(tmp_path, OTHER)
    (other / "secret.txt").write_text("nope")
    (root / "index.js").write_bytes(NODE_PROBE)
    monkeypatch.setenv("PLUGIN_HOST_SECRET", "host-secret")
    argv = bwrap_argv(PID, 20000, root, state, "node", "index.js", data_dir=tmp_path)
    argv += [str(other / "secret.txt"), str(tmp_path / "plugins")]
    out = subprocess.run(argv, env=plugin_env(_env(), 9100), capture_output=True, timeout=30)
    assert out.stdout.decode().strip() == "no-other,no-data,wrote-state,ro-code,no-leak"
    assert (state / "ok").read_text() == "w"


@pytest.mark.sandbox
@needs_sandbox
def test_self_test_passes_in_image() -> None:
    assert sandbox.self_test() is True


def test_self_test_probes_full_namespace_set(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(sandbox, "MOUNTPOINTS", ())
    monkeypatch.setattr(sandbox, "_bwrap_ok", lambda a: calls.append(a) or True)
    assert sandbox.self_test() is True
    assert calls[0] == ["--ro-bind", "/", "/", "true"]
    assert {"--proc", "--unshare-pid", "--unshare-ipc", "--cap-drop"} <= set(calls[1])
