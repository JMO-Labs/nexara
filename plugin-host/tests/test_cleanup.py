"""
@file
@brief Owner-delete cleanup: argv, uid process polling, logged failures, and (image only)
       real deletion of a plugin-owned 0700 tree by a root host without DAC_OVERRIDE.
"""

import logging
import os
import shutil
import tempfile
from pathlib import Path

import pytest

from host import cleanup, perms, sandbox

UID = 20000


def test_remove_argv_binds_only_target(tmp_path: Path) -> None:
    target = tmp_path / "plugin-state" / "dev.nexara.echo"
    target.mkdir(parents=True)
    argv = cleanup.remove_argv(target, UID, tmp_path, 7)
    head = argv[argv.index("bwrap") + 1 : argv.index("--")]
    binds = [head[i + 1] for i, a in enumerate(head) if a == "--bind"]
    assert binds == [str(target)]
    assert head[head.index("--uid") + 1] == str(UID) and "--seccomp" in head
    assert head[head.index("--chdir") + 1] == "/"  # never chdir into the plugin's tree
    assert argv[argv.index("--") + 1 :] == [*cleanup.OWNER_CMD, str(target)]
    assert 'chmod u+rwx -- "$1"' in cleanup.OWNER_CMD[2]
    with pytest.raises(ValueError):
        cleanup.remove_argv(Path("/etc"), UID, tmp_path, 7)


def _status(proc: Path, pid: int, uid: int, state: str = "S (sleeping)") -> None:
    (proc / str(pid)).mkdir()
    (proc / str(pid) / "status").write_text(
        f"Name:\tx\nState:\t{state}\nUid:\t{uid}\t{uid}\t{uid}\t{uid}\n"
    )


async def test_wait_uid_gone(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cleanup, "PROC", tmp_path)
    _status(tmp_path, 10, 0)
    _status(tmp_path, 11, UID)
    _status(tmp_path, 12, UID, "Z (zombie)")  # zombies hold nothing: ignored
    (tmp_path / "self").mkdir()
    assert cleanup.uid_processes(UID) == [11]
    assert await cleanup.wait_uid_gone(UID, timeout=0.1) is False
    shutil.rmtree(tmp_path / "11")
    assert await cleanup.wait_uid_gone(UID, timeout=0.1) is True


async def test_remove_tree_logs_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    d = tmp_path / "plugins" / "x"
    (d / "sub").mkdir(parents=True)
    (d / "sub" / "f").write_text("1")
    assert await cleanup.remove_tree(d, None, tmp_path) is True and not d.exists()
    assert await cleanup.remove_tree(d, None, tmp_path) is True  # already gone

    def boom(path: object, onexc: object) -> None:
        onexc(os.rmdir, str(path), PermissionError())  # type: ignore[operator]

    (d / "sub").mkdir(parents=True)
    monkeypatch.setattr(cleanup.shutil, "rmtree", boom)
    with caplog.at_level(logging.ERROR):
        assert await cleanup.remove_tree(d, None, tmp_path) is False
    assert "PermissionError" in caplog.text and "not fully removed" in caplog.text


def _chmod_as(path: Path, uid: int, mode: int) -> None:
    """@brief chmod as the owner uid (root without CAP_FOWNER cannot)."""
    import subprocess

    subprocess.run(["chmod", oct(mode)[2:], str(path)], check=True, **perms.as_user(uid))


_CAN = (
    shutil.which("bwrap") is not None
    and all(p.is_dir() for p in sandbox.MOUNTPOINTS)
    and os.geteuid() == 0
)


@pytest.mark.sandbox
@pytest.mark.skipif(not _CAN, reason="needs root + bwrap + image mountpoints")
@pytest.mark.parametrize("top_mode", [0o700, 0o000])
async def test_owner_delete_of_hostile_tree(top_mode: int) -> None:
    data = Path(tempfile.mkdtemp())
    data.chmod(0o755)
    state = data / "plugin-state" / "dev.nexara.echo"
    (data / "plugin-state").mkdir(mode=0o755)
    # build the hostile tree as the plugin would: 0700 / 000 dirs owned by the uid
    os.makedirs(state / "a" / "b")
    (state / "a" / "b" / "f").write_text("x")
    # chmod while still root-owned (no CAP_FOWNER), innermost first
    os.chown(state / "a" / "b" / "f", UID, UID)
    (state / "a" / "b").chmod(0)
    os.chown(state / "a" / "b", UID, UID)
    (state / "a").chmod(0o700)
    os.chown(state / "a", UID, UID)
    perms.prepare_state(state, UID)
    _chmod_as(state, UID, top_mode)  # the plugin owns its state dir and may lock it
    try:
        assert await cleanup.remove_tree(state, UID, data) is True
        assert not state.exists()
    finally:
        shutil.rmtree(data, ignore_errors=True)
