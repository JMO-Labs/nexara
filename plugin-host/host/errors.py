"""
@file
@brief Installer error types shared by download, archive and deps modules, plus a
       secret-free exception description for logs.
"""


class InstallError(Exception):
    """@brief Install failure; `code` is reported as last_error (fixed text, never secrets)."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class SandboxUnavailableError(Exception):
    """@brief bwrap self-test failed at startup; no plugin may start."""


def describe_error(e: BaseException) -> str:
    """
    @brief Safe one-line diagnosis for logs: exception type, the failing path(s) of an
    OSError and the innermost host frame. Never the message (it may embed the spec,
    a URL or subprocess output).
    """
    out = type(e).__name__
    if isinstance(e, OSError):
        if e.errno is not None:
            out += f" errno={e.errno}"
        paths = [str(p) for p in (e.filename, e.filename2) if p is not None]
        if paths:
            out += " path=" + " -> ".join(paths)
    tb, frame = e.__traceback__, None
    while tb is not None:
        if tb.tb_frame.f_globals.get("__name__", "").startswith("host."):
            frame = tb
        tb = tb.tb_next
    if frame is not None:
        code = frame.tb_frame.f_code
        out += f" at {frame.tb_frame.f_globals['__name__']}.{code.co_name}:{frame.tb_lineno}"
    return out
