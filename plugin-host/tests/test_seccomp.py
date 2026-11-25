"""
@file
@brief Seccomp filter behaviour under real bwrap (runs wherever unprivileged bwrap works).
"""

import os
import shutil
import subprocess
import sys

import pytest

from host import perms, seccomp

PROBE = r"""
import ctypes, errno, os
libc = ctypes.CDLL(None, use_errno=True)
def call(nr, *args):
    r = libc.syscall(nr, *[ctypes.c_long(a) for a in args])
    return "ok" if r >= 0 else errno.errorcode[ctypes.get_errno()]
NR = {"io_uring_setup": 425, "personality": 135, "open_by_handle_at": 304,
      "name_to_handle_at": 303, "unshare": 272, "getpid": 39}
out = [
    "io_uring=" + call(NR["io_uring_setup"], 1, 0),
    "pers_query=" + call(NR["personality"], 0xFFFFFFFF),
    "pers_linux=" + call(NR["personality"], 0),
    "pers_linux32=" + call(NR["personality"], 0x0008),
    "pers_rie=" + call(NR["personality"], 0x0400000),
    "pers_norand=" + call(NR["personality"], 0x0040000),
    "obh=" + call(NR["open_by_handle_at"], -1, 0, 0),
    "nth=" + call(NR["name_to_handle_at"], -100, 0, 0, 0, 0),
    "userns=" + call(NR["unshare"], 0x10000000),
    "getpid=" + call(NR["getpid"]),
]
print(" ".join(out))
"""


@pytest.mark.skipif(
    shutil.which("bwrap") is None or os.uname().machine != "x86_64",
    reason="needs bwrap on x86_64 (syscall numbers)",
)
def test_filter_blocks_attack_surface() -> None:
    fd = seccomp.filter_fd()
    if fd is None:
        pytest.skip("libseccomp not available")
    argv = ["bwrap", "--ro-bind", "/", "/", "--dev", "/dev", "--unshare-pid"]
    argv += ["--seccomp", str(fd), "--", sys.executable, "-I", "-c", PROBE]
    r = subprocess.run(
        argv,
        pass_fds=(fd,),
        capture_output=True,
        text=True,
        timeout=30,
        **perms.as_user(perms.PROBE_UID),  # root without CAP_SYS_ADMIN cannot unshare
    )
    os.close(fd)
    if "No permissions to create a new namespace" in r.stderr:
        pytest.skip("unprivileged user namespaces disabled here")
    got = dict(kv.split("=") for kv in r.stdout.split())
    assert got == {
        "io_uring": "EPERM",
        "pers_query": "EPERM",
        "pers_linux": "ok",
        "pers_linux32": "ok",
        "pers_rie": "EPERM",
        "pers_norand": "EPERM",
        "obh": "EPERM",
        "nth": "EPERM",
        "userns": "EPERM",
        "getpid": "ok",
    }, r.stderr
