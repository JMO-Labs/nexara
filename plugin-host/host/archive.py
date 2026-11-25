"""
@file
@brief Safe single-pass .tar.gz extraction. Only regular files and directories;
       rejects absolute paths, `..`, links, devices, duplicates, tool config files,
       and caps decompressed bytes (headers included) and member count.
"""

import gzip
import io
import tarfile
from collections.abc import Iterator
from pathlib import Path, PurePosixPath

from host.errors import InstallError

MAX_EXTRACT_BYTES = 200 * 1024 * 1024
MAX_MEMBERS = 10_000
# Tool config and alternate lockfiles: npm ci must only ever see the validated
# package-lock.json (npm-shrinkwrap.json takes precedence over it).
FORBIDDEN_FILES = frozenset(
    {".npmrc", ".yarnrc", ".yarnrc.yml", ".pnpmfile.cjs", "pip.conf", "pip.ini", "uv.toml",
     ".python-version", "npm-shrinkwrap.json", "yarn.lock", "pnpm-lock.yaml", "bun.lockb",
     "bun.lock"}
)  # fmt: skip
# Built by the installer; a shipped copy could plant an interpreter or modules.
FORBIDDEN_TOP_DIRS = frozenset({".venv", "node_modules"})


class _CappedReader(io.RawIOBase):
    """@brief Read-only stream that fails once more than `cap` bytes were read."""

    def __init__(self, inner: gzip.GzipFile, cap: int) -> None:
        self._inner, self._left = inner, cap

    def readable(self) -> bool:
        return True

    def read(self, size: int = -1) -> bytes:
        if size is None or size < 0 or size > self._left + 1:
            size = self._left + 1
        data = self._inner.read(size)
        self._left -= len(data)
        if self._left < 0:
            raise InstallError("unsafe_archive")
        return data


def _checked(tf: tarfile.TarFile) -> Iterator[tarfile.TarInfo]:
    """@brief Yield members lazily, rejecting anything unsafe before it is extracted."""
    seen: set[PurePosixPath] = set()
    total = 0
    for m in tf:
        name = PurePosixPath(m.name)
        if m.name.startswith(("/", "\\")) or ".." in name.parts or "\0" in m.name:
            raise InstallError("unsafe_archive")
        if not (m.isfile() or m.isdir()):
            raise InstallError("unsafe_archive")
        if name.name.lower() in FORBIDDEN_FILES:
            raise InstallError("forbidden_config_file")
        if name.parts and name.parts[0].lower() in FORBIDDEN_TOP_DIRS:
            raise InstallError("unsafe_archive")
        if name in seen:
            raise InstallError("unsafe_archive")
        seen.add(name)
        total += m.size
        if total > MAX_EXTRACT_BYTES or len(seen) > MAX_MEMBERS:
            raise InstallError("unsafe_archive")
        yield m


def safe_extract(data: bytes, dest: Path) -> None:
    """
    @brief Extract gzip'd tar `data` into existing dir `dest` in one streaming pass.
    Partial output may remain on error; the caller removes `dest`.
    """
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(data)) as gz:
            reader = _CappedReader(gz, MAX_EXTRACT_BYTES)
            with tarfile.open(fileobj=reader, mode="r|") as tf:
                tf.extractall(dest, members=_checked(tf), filter="data")
    except MemoryError as e:
        raise InstallError("unsafe_archive") from e
    except (tarfile.TarError, OSError, EOFError, gzip.BadGzipFile) as e:
        raise InstallError("invalid_archive") from e
