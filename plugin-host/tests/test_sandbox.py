"""
@file
@brief bwrap argv / env / limits / uid + ownership unit tests, plus real-bwrap
       integration tests (marker `sandbox`; they need bwrap, libseccomp and the image's
       /plugin + /state mountpoints, and run as root to drop to a plugin uid).
"""

import json
import os
import shutil
import subprocess
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

from host import perms, sandbox, seccomp
from host.models import PluginEnv
from host.perms import plugin_uid
from host.sandbox import bwrap_argv, install_argv, plugin_env

PID = "dev.nexara.echo"
OTHER = "dev.nexara.other"
FD = 7
BIND_OPTS = {"--bind", "--ro-bind", "--dev-bind", "--bind-try", "--ro-bind-try", "--dev-bind-try"}


def _dirs(data: Path, pid: str = PID) -> tuple[Path, Path]:
    root = data / "plugins" / pid / "1.0.0"
    state = data / "plugin-state" / pid
    root.mkdir(parents=True)
    state.mkdir(parents=True)
    return root, state


def _argv(
    data: Path, root: Path, state: Path, runtime: str = "node", ep: str = "index.js"
) -> list[str]:
    return bwrap_argv(PID, 20000, root, state, runtime, ep, seccomp_fd=FD, data_dir=data)


def _head(argv: list[str]) -> list[str]:
    """@brief bwrap options: after `bwrap`, before the `--` separator."""
    return argv[argv.index("bwrap") + 1 : argv.index("--")]


def _binds(argv: list[str]) -> list[tuple[str, str]]:
    head = _head(argv)
    return [(head[i + 1], head[i + 2]) for i, a in enumerate(head) if a in BIND_OPTS]


def _writable(argv: list[str]) -> list[str]:
    head = _head(argv)
    return [head[i + 1] for i, a in enumerate(head) if a in {"--bind", "--dev-bind"}]


def test_argv_layout(tmp_path: Path) -> None:
    root, state = _dirs(tmp_path)
    argv = _argv(tmp_path, root, state)
    joined = " ".join(argv)
    order = [
        "prlimit --nproc=",
        "bwrap --ro-bind / /",
        "--tmpfs /tmp",
        f"--tmpfs {tmp_path}",
        f"--ro-bind {root} /plugin",
        f"--bind {state} /state",
        "--dev /dev",
        f"--seccomp {FD}",
    ]
    idx = [joined.index(o) for o in order]
    assert idx == sorted(idx)
    for flag in ("--unshare-pid", "--unshare-ipc", "--die-with-parent", "--new-session"):
        assert flag in argv
    assert "--proc" not in argv  # container's masked /proc; no systempaths=unconfined
    assert argv[argv.index("--chdir") + 1] == "/plugin"
    assert argv[argv.index("--") :] == ["--", "node", "index.js"]


def test_limits_and_tmpfs_sizes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root, state = _dirs(tmp_path)
    argv = _argv(tmp_path, root, state)
    assert argv[: argv.index("bwrap")] == [
        "prlimit",
        "--nproc=256",
        f"--as={4096 * 1024 * 1024}",
        f"--fsize={1024 * 1024 * 1024}",
        "--nofile=1024",
    ]
    head = _head(argv)
    tmpfs = [i for i, a in enumerate(head) if a == "--tmpfs"]
    assert len(tmpfs) == 2
    assert all(head[i - 2 : i] == ["--size", str(64 * 1024 * 1024)] for i in tmpfs)
    monkeypatch.setenv("PLUGIN_LIMIT_NPROC", "32")
    monkeypatch.setenv("PLUGIN_LIMIT_AS_MB", "bogus")  # invalid → default
    monkeypatch.setenv("PLUGIN_TMPFS_MB", "8")
    argv = _argv(tmp_path, root, state)
    assert "--nproc=32" in argv and f"--as={4096 * 1024 * 1024}" in argv
    assert str(8 * 1024 * 1024) in argv


def test_argv_python_uses_venv_interpreter(tmp_path: Path) -> None:
    root, state = _dirs(tmp_path)
    argv = _argv(tmp_path, root, state, "python", "echo.py")
    assert argv[argv.index("--") :] == ["--", "/plugin/.venv/bin/python", "-u", "echo.py"]


def test_argv_never_binds_other_plugin(tmp_path: Path) -> None:
    root, state = _dirs(tmp_path)
    _dirs(tmp_path, OTHER)
    argv = _argv(tmp_path, root, state)
    assert {s for s, _ in _binds(argv)} == {"/", str(root), str(state)}
    assert not any(OTHER in a for a in argv)


@pytest.mark.parametrize(
    "root_of,state_of", [(OTHER, PID), (PID, OTHER), (f"{PID}/../{OTHER}", PID)]
)
def test_argv_rejects_foreign_dirs(tmp_path: Path, root_of: str, state_of: str) -> None:
    _dirs(tmp_path)
    _dirs(tmp_path, OTHER)
    root = tmp_path / "plugins" / root_of / "1.0.0"
    with pytest.raises(ValueError):
        _argv(tmp_path, root, tmp_path / "plugin-state" / state_of)


def test_argv_rejects_symlinked_root(tmp_path: Path) -> None:
    _, state = _dirs(tmp_path)
    other, _ = _dirs(tmp_path, OTHER)
    link = tmp_path / "plugins" / PID / "2.0.0"
    link.symlink_to(other)
    with pytest.raises(ValueError):
        _argv(tmp_path, link, state)


def test_runtime_code_read_only_and_cache_never_mounted(tmp_path: Path) -> None:
    root, state = _dirs(tmp_path)
    (root.parent / ".cache").mkdir()
    argv = _argv(tmp_path, root, state, "python", "echo.py")
    assert _writable(argv) == [str(state)]
    assert not any(".cache" in a for a in argv)
    head = _head(argv)
    i = head.index(str(root))
    assert head[i - 1 : i + 2] == ["--ro-bind", str(root), "/plugin"]


def test_install_argv_binds_only_version_and_cache(tmp_path: Path) -> None:
    root, _ = _dirs(tmp_path)
    _dirs(tmp_path, OTHER)
    cache = root.parent / ".cache"
    argv = install_argv(["npm", "ci"], root, 20000, tmp_path, seccomp_fd=FD)
    assert set(_binds(argv)) == {("/", "/"), (str(root), str(root)), (str(cache), str(cache))}
    assert set(_writable(argv)) == {str(root), str(cache)}
    assert f"--tmpfs {tmp_path}" in " ".join(argv) and argv[0] == "prlimit"
    assert argv[argv.index("--seccomp") + 1] == str(FD) and "--proc" not in argv
    assert argv[argv.index("--chdir") + 1] == str(root)
    assert argv[argv.index("--") :] == ["--", "npm", "ci"]
    with pytest.raises(ValueError):
        install_argv(["npm", "ci"], tmp_path / "plugins", 20000, tmp_path, seccomp_fd=FD)


@pytest.mark.parametrize(
    "mode,want", [(0o644, 0o640), (0o600, 0o640), (0o755, 0o750), (0o4777, 0o750), (0o2700, 0o750)]
)
def test_sealed_mode_never_group_or_other_writable(mode: int, want: int) -> None:
    assert perms.sealed_mode(mode) == want


def _env() -> PluginEnv:
    return PluginEnv(
        NEXARA_TOKEN="tok",
        NEXARA_WEBHOOK_SECRET="whs",
        NEXARA_SETTINGS={"a": 1},  # type: ignore[arg-type]
    )


def test_plugin_env_is_exact(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PLUGIN_HOST_SECRET", "host-secret")
    monkeypatch.setenv("NEXARA_URL", "http://nexara:8080")
    assert plugin_env(_env(), 9100) == {
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


def test_chown_tree_skips_when_not_root(tmp_path: Path) -> None:
    (tmp_path / "f").write_text("x")
    perms.chown_tree(tmp_path, 20000)  # non-root: no-op, must not raise
    if os.geteuid() != 0:
        assert (tmp_path / "f").stat().st_uid == os.geteuid()


def test_self_test_fails_without_bwrap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sandbox, "MOUNTPOINTS", ())
    monkeypatch.setattr(sandbox, "BWRAP", "/nonexistent/bwrap")
    assert sandbox.self_test() is False


def test_self_test_requires_mountpoints(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(sandbox, "MOUNTPOINTS", (tmp_path / "missing",))
    assert sandbox.self_test() is False


def test_self_test_probes_real_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(sandbox, "MOUNTPOINTS", ())
    monkeypatch.setattr(seccomp, "filter_fd", lambda: os.open(os.devnull, os.O_RDONLY))
    monkeypatch.setattr(sandbox, "_probe", lambda a, fd=None: calls.append(a) or True)
    assert sandbox.self_test() is True
    assert calls[0] == ["bwrap", "--ro-bind", "/", "/", "true"]
    probe = calls[1]
    assert probe[0] == "prlimit" and "--proc" not in probe and "--seccomp" in probe
    assert {"--unshare-pid", "--unshare-ipc", "--cap-drop", "--size"} <= set(probe)


def test_self_test_fails_without_seccomp(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sandbox, "MOUNTPOINTS", ())
    monkeypatch.setattr(sandbox, "_probe", lambda a, fd=None: True)
    monkeypatch.setattr(seccomp, "filter_fd", lambda: None)
    assert sandbox.self_test() is False


def test_seccomp_filter_compiles_when_libseccomp_present() -> None:
    if seccomp.filter_bytes() is None:
        pytest.skip("libseccomp not available")
    bpf = seccomp.filter_bytes()
    assert bpf and len(bpf) % 8 == 0  # struct sock_filter = 8 bytes


# --- integration: real bwrap as a plugin uid, image only ---------------------------------

_CAN_SANDBOX = (
    shutil.which("bwrap") is not None
    and all(p.is_dir() for p in sandbox.MOUNTPOINTS)
    and os.geteuid() == 0
)
needs_sandbox = pytest.mark.skipif(not _CAN_SANDBOX, reason="needs root + bwrap + /plugin,/state")

NODE_PROBE = b"""
const fs = require('fs'), cp = require('child_process');
const out = [];
try { fs.readFileSync(process.argv[2]); out.push('read-other'); }
catch (e) { out.push('no-other'); }
try { fs.readdirSync(process.argv[3]); out.push('list-data'); }
catch (e) { out.push('no-data'); }
fs.writeFileSync('/state/ok', 'w'); out.push('wrote-state');
try { fs.writeFileSync('/plugin/x', 'w'); out.push('wrote-code'); }
catch (e) { out.push('ro-code'); }
out.push(process.env.PLUGIN_HOST_SECRET ? 'leak' : 'no-leak');
try { cp.execSync('unshare -U true', {stdio: 'ignore'}); out.push('userns'); }
catch (e) { out.push('no-userns'); }
console.log(out.join(','));
"""


@pytest.fixture
def data() -> Iterator[Path]:
    d = Path(tempfile.mkdtemp())
    d.chmod(0o755)  # plugin uid must traverse to its bind sources
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.mark.sandbox
@needs_sandbox
@pytest.mark.skipif(shutil.which("node") is None, reason="needs node")
def test_node_plugin_isolated(data: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root, state = _dirs(data)
    other, _ = _dirs(data, OTHER)
    (other / "secret.txt").write_text("nope")
    (root / "index.js").write_bytes(NODE_PROBE)
    for d in (data / "plugins", data / "plugins" / PID):
        d.chmod(0o755)
    perms.seal_tree(root, 20000)
    perms.prepare_state(state, 20000)
    monkeypatch.setenv("PLUGIN_HOST_SECRET", "host-secret")
    fd = seccomp.filter_fd()
    assert fd is not None
    argv = bwrap_argv(PID, 20000, root, state, "node", "index.js", seccomp_fd=fd, data_dir=data)
    argv += [str(other / "secret.txt"), str(data / "plugins")]
    out = subprocess.run(
        argv,
        env=plugin_env(_env(), 9100),
        capture_output=True,
        timeout=30,
        pass_fds=(fd,),
        **perms.as_user(20000),
    )
    os.close(fd)
    assert out.stdout.decode().strip() == (
        "no-other,no-data,wrote-state,ro-code,no-leak,no-userns"
    ), out.stderr.decode()


@pytest.mark.sandbox
@needs_sandbox
def test_self_test_passes_in_image(data: Path) -> None:
    assert sandbox.self_test(data) is True
