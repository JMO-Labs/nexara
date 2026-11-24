"""
@file
@brief Seccomp filter for plugin sandboxes, compiled once via libseccomp (ctypes) and
       handed to bwrap with `--seccomp <fd>`.

Allow by default; EPERM for kernel-attack-surface syscalls plugins never need
(ptrace, bpf, keyrings, perf, userfaultfd, kexec, mount family, setns) and for
clone/unshare with CLONE_NEWUSER. clone3 gets ENOSYS (its flags live in memory the
filter cannot read) so libc falls back to clone. Foreign arches (i386/x32) are killed
by libseccomp's default bad-arch action. No filter → sandbox unavailable (fail closed).
"""

import ctypes
import errno
import functools
import logging
import os

log = logging.getLogger(__name__)

LIBSECCOMP = "libseccomp.so.2"
SCMP_ACT_ALLOW = 0x7FFF0000
SCMP_CMP_MASKED_EQ = 7
CLONE_NEWUSER = 0x10000000

DENY = (
    "ptrace", "process_vm_readv", "process_vm_writev",
    "bpf", "perf_event_open", "userfaultfd",
    "keyctl", "add_key", "request_key",
    "kexec_load", "kexec_file_load",
    "mount", "umount2", "pivot_root", "chroot", "setns",
    "fsopen", "fsconfig", "fsmount", "fspick", "move_mount", "open_tree", "mount_setattr",
)  # fmt: skip
NO_NEWUSER = ("clone", "unshare")  # flags are arg 0 on x86_64 and aarch64


class _ArgCmp(ctypes.Structure):
    _fields_ = [
        ("arg", ctypes.c_uint),
        ("op", ctypes.c_int),
        ("datum_a", ctypes.c_uint64),
        ("datum_b", ctypes.c_uint64),
    ]


def _errno_action(err: int) -> int:
    return 0x00050000 | (err & 0xFFFF)


def _compile() -> bytes:
    lib = ctypes.CDLL(LIBSECCOMP, use_errno=True)
    lib.seccomp_init.restype = ctypes.c_void_p
    lib.seccomp_init.argtypes = [ctypes.c_uint32]
    lib.seccomp_rule_add_array.argtypes = [
        ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_uint, ctypes.POINTER(_ArgCmp)
    ]  # fmt: skip
    lib.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    lib.seccomp_export_bpf.argtypes = [ctypes.c_void_p, ctypes.c_int]
    lib.seccomp_release.argtypes = [ctypes.c_void_p]

    ctx = lib.seccomp_init(SCMP_ACT_ALLOW)
    if not ctx:
        raise OSError("seccomp_init failed")
    try:

        def add(name: str, action: int, cmp: _ArgCmp | None = None) -> None:
            nr = lib.seccomp_syscall_resolve_name(name.encode())
            if nr < 0:  # not on this arch
                return
            arr = (_ArgCmp * 1)(cmp) if cmp else None
            if lib.seccomp_rule_add_array(ctx, action, nr, 1 if cmp else 0, arr) != 0:
                raise OSError(f"seccomp rule for {name} failed")

        for name in DENY:
            add(name, _errno_action(errno.EPERM))
        newuser = _ArgCmp(0, SCMP_CMP_MASKED_EQ, CLONE_NEWUSER, CLONE_NEWUSER)
        for name in NO_NEWUSER:
            add(name, _errno_action(errno.EPERM), newuser)
        add("clone3", _errno_action(errno.ENOSYS))
        r, w = os.pipe()  # program is a few hundred bytes: fits the pipe buffer
        try:
            rc = lib.seccomp_export_bpf(ctx, w)
            os.close(w)
            w = -1
            if rc != 0:
                raise OSError("seccomp_export_bpf failed")
            return os.read(r, 1 << 16)
        finally:
            os.close(r)
            if w >= 0:
                os.close(w)
    finally:
        lib.seccomp_release(ctx)


@functools.cache
def filter_bytes() -> bytes | None:
    """@brief The compiled BPF program, or None if libseccomp is unusable (logged once)."""
    try:
        return _compile()
    except (OSError, AttributeError) as e:
        log.error("seccomp filter unavailable: %s", e)
        return None


def filter_fd() -> int | None:
    """
    @brief Read end of a pipe pre-filled with the filter (bwrap reads it to EOF).
    The fd is CLOEXEC (pass it via pass_fds); the caller closes it after spawning.
    """
    bpf = filter_bytes()
    if bpf is None:
        return None
    r, w = os.pipe()
    os.write(w, bpf)
    os.close(w)
    return r
