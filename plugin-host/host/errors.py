"""
@file
@brief Installer error type shared by download, archive and deps modules.
"""


class InstallError(Exception):
    """@brief Install failure; `code` is reported as last_error (fixed text, never secrets)."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class SandboxUnavailableError(Exception):
    """@brief bwrap self-test failed at startup; no plugin may start."""
