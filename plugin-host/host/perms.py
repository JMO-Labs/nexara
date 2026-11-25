"""
@file
@brief Per-plugin uid allocation and file ownership: install-time hand-over to the
       plugin uid, runtime sealing (read-only for the plugin), Popen credentials.
"""

import json
import os
import stat
from pathlib import Path
from typing import TypedDict

UID_BASE = 20000
PROBE_UID = UID_BASE - 1  # self-test runs as this unprivileged uid


def plugin_uid(data_dir: Path, plugin_id: str) -> int:
    """@brief UID_BASE + stable index from <data>/uids.json (allocated on first use, kept)."""
    path = data_dir / "uids.json"
    uids: dict[str, int] = json.loads(path.read_text()) if path.exists() else {}
    if plugin_id not in uids:
        uids[plugin_id] = max(uids.values(), default=-1) + 1
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(uids))
        os.replace(tmp, path)
    return UID_BASE + uids[plugin_id]


def is_root() -> bool:
    return os.geteuid() == 0


def _retree(path: str, owner: int, group: int, seal: bool) -> None:
    """
    @brief Re-own one tree as root WITHOUT CAP_DAC_OVERRIDE: each dir is first taken
    over (root:root 0700) so it can be listed even if it was a plugin's 0000 dir, then
    its entries are handled, then it gets its final owner/mode. Symlinks are re-owned,
    never followed. Only runs while no process of the plugin uid is alive.
    """
    st = os.lstat(path)
    if stat.S_ISDIR(st.st_mode):
        os.chown(path, 0, 0, follow_symlinks=False)
        os.chmod(path, 0o700)
        with os.scandir(path) as it:
            names = [e.name for e in it]
        for name in names:
            _retree(os.path.join(path, name), owner, group, seal)
    elif stat.S_ISLNK(st.st_mode):
        os.chown(path, owner, group, follow_symlinks=False)
        return
    else:
        os.chown(path, 0, 0, follow_symlinks=False)
    mode = sealed_mode(st.st_mode) if seal else stat.S_IMODE(st.st_mode)
    os.chmod(path, mode)  # while root-owned (no CAP_FOWNER needed)
    os.chown(path, owner, group, follow_symlinks=False)


def chown_tree(path: Path, uid: int) -> None:
    """@brief chown -R uid:uid, modes kept (install time: the plugin may write it). Root only."""
    if is_root() and path.exists():
        _retree(str(path), uid, uid, seal=False)


def sealed_mode(mode: int) -> int:
    """@brief Owner bits kept (no setuid/setgid/sticky); group r + x-if-owner-x; other none."""
    owner = stat.S_IMODE(mode) & 0o700
    return owner | 0o040 | (0o010 if owner & 0o100 else 0)


def seal_tree(path: Path, uid: int) -> None:
    """
    @brief After install: root:uid, group read(+exec where owner has it), no group/other
    write. The plugin can read its code and cache but never modify them. Root only.
    """
    if is_root() and path.exists():
        _retree(str(path), 0, uid, seal=True)


def prepare_state(state: Path, uid: int) -> None:
    """@brief Create the plugin's state dir, owned by its uid, mode 0700."""
    state.mkdir(mode=0o700, parents=True, exist_ok=True)
    if state.is_symlink():
        raise ValueError("state dir is a symlink")
    if is_root() and state.lstat().st_uid != uid:
        state.chmod(0o700)  # while still root-owned (no CAP_FOWNER needed)
        os.chown(state, uid, uid, follow_symlinks=False)


class Creds(TypedDict):
    """@brief Popen kwargs that drop to a plugin uid (empty supplementary groups)."""

    user: int | None
    group: int | None
    extra_groups: list[int] | None


def as_user(uid: int | None) -> Creds:
    """@brief Popen kwargs to drop to `uid` (only possible, and required, as root)."""
    if uid is None or not is_root():
        return Creds(user=None, group=None, extra_groups=None)
    return Creds(user=uid, group=uid, extra_groups=[])


def set_nondumpable() -> None:
    """
    @brief prctl(PR_SET_DUMPABLE, 0): /proc/<host>/* becomes root-owned, so even a
    same-uid process (insecure dev mode) cannot read the host's environ/memory.
    """
    import ctypes

    try:
        ctypes.CDLL(None, use_errno=True).prctl(4, 0, 0, 0, 0)  # PR_SET_DUMPABLE
    except (OSError, AttributeError):
        pass
