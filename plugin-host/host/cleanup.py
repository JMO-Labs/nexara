"""
@file
@brief Delete plugin-owned trees without root ever traversing plugin-controlled paths.

The host runs as root WITHOUT CAP_DAC_OVERRIDE, so it cannot enter a plugin's 0700
dirs. Instead the owner deletes: `find -delete` as the plugin uid inside bwrap with only
that tree bound; root then removes what is left (root-owned, sealed parts) and the top
dir (root owns the parent). Runs only once the plugin uid has no live processes.
"""

import asyncio
import logging
import os
import shutil
import subprocess
from pathlib import Path

from host import perms, seccomp
from host.sandbox import _common, _tail

log = logging.getLogger(__name__)

PROC = Path("/proc")
GONE_TIMEOUT_S = 5.0
OWNER_TIMEOUT_S = 120
# $1 = the tree. The owner can always chmod its own top dir (even if it set 0000), so
# never chdir into it; the parent comes from the bwrap tmpfs (0755).
OWNER_CMD = [
    "sh",
    "-c",
    'chmod u+rwx -- "$1"; chmod -R u+rwX -- "$1" 2>/dev/null; '
    'find "$1" -mindepth 1 -delete 2>/dev/null',
    "sh",
]


def remove_argv(path: Path, uid: int, data_dir: Path, seccomp_fd: int) -> list[str]:
    """@brief bwrap argv deleting the contents of `path` as `uid` (only `path` writable)."""
    real = path.resolve()
    if data_dir.resolve() not in real.parents:
        raise ValueError("refusing to delete outside the data dir")
    return [
        *_common(data_dir),
        "--bind", str(real), str(real),
        *_tail(uid, seccomp_fd),
        "--remount-ro", str(data_dir),
        "--chdir", "/",
        "--", *OWNER_CMD, str(real),
    ]  # fmt: skip


def uid_processes(uid: int) -> list[int]:
    """@brief Live (non-zombie) pids whose real uid is `uid`."""
    pids = []
    for d in PROC.iterdir():
        if not d.name.isdigit():
            continue
        try:
            fields = dict(
                ln.split(":", 1) for ln in (d / "status").read_text().splitlines() if ":" in ln
            )
            if fields["State"].split()[0] != "Z" and int(fields["Uid"].split()[0]) == uid:
                pids.append(int(d.name))
        except (OSError, ValueError, IndexError, KeyError):
            continue
    return pids


async def wait_uid_gone(uid: int, timeout: float = GONE_TIMEOUT_S) -> bool:
    """@brief Poll until `uid` has no processes (namespace teardown can lag the wait())."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while uid_processes(uid):
        if loop.time() >= deadline:
            log.error("uid %s still has processes; deleting anyway", uid)
            return False
        await asyncio.sleep(0.05)
    return True


def _owner_pass(path: Path, uid: int, data_dir: Path) -> None:
    fd = seccomp.filter_fd()
    if fd is None:
        log.error("no seccomp filter: skipping owner delete of %s", path.name)
        return
    try:
        subprocess.run(
            remove_argv(path, uid, data_dir, fd),
            env={"PATH": "/usr/bin:/bin"},
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=OWNER_TIMEOUT_S,
            pass_fds=(fd,),
            **perms.as_user(uid),
        )
    except (OSError, subprocess.SubprocessError, ValueError) as e:
        log.error("owner delete of %s failed: %s", path.name, type(e).__name__)
    finally:
        os.close(fd)


async def remove_tree(path: Path, uid: int | None, data_dir: Path) -> bool:
    """
    @brief Remove `path` (a dir under data_dir); failures are logged, never silent.
    @param uid Plugin uid owning (parts of) the tree; None = root-owned only.
    @return True if `path` is gone.
    """
    if path.is_symlink():
        path.unlink()
        return True
    if not path.exists():
        return True
    if uid is not None and perms.is_root():
        await wait_uid_gone(uid)
        await asyncio.to_thread(_owner_pass, path, uid, data_dir)
        # take over only the (now empty) top dir so root can list and remove it
        os.chown(path, 0, 0, follow_symlinks=False)
        os.chmod(path, 0o700)

    def onexc(func: object, p: str, exc: BaseException) -> None:
        log.error("cannot remove %s: %s", p, type(exc).__name__)

    await asyncio.to_thread(shutil.rmtree, path, onexc=onexc)
    if path.exists():
        log.error("%s was not fully removed", path)
        return False
    return True
