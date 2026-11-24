"""
@file
@brief Safe extraction tests: traversal, links, devices, forbidden config, bombs.
"""

import io
import tarfile
from pathlib import Path

import pytest

from host import archive
from host.archive import safe_extract
from host.installer import InstallError
from tests.conftest import make_tar, manifest

BASE = {"nexara-plugin.toml": manifest(), "echo.py": b""}


def _add(kind: bytes, name: str, link: str = "") -> object:
    def hook(tf: tarfile.TarFile) -> None:
        info = tarfile.TarInfo(name)
        info.type = kind
        info.linkname = link
        tf.addfile(info)

    return hook


def code_of(data: bytes, dest: Path) -> str:
    with pytest.raises(InstallError) as e:
        safe_extract(data, dest)
    return e.value.code


def test_extracts_regular_files(tmp_path: Path) -> None:
    safe_extract(make_tar({**BASE, "lib/a.py": b"x"}), tmp_path)
    assert (tmp_path / "lib" / "a.py").read_bytes() == b"x"


@pytest.mark.parametrize(
    "data",
    [
        make_tar({**BASE, "../x": b"evil"}),
        make_tar({**BASE, "a/../../x": b"evil"}),
        make_tar({**BASE, "/abs": b"evil"}),
        make_tar(BASE, _add(tarfile.SYMTYPE, "link", "/etc/passwd")),  # type: ignore[arg-type]
        make_tar(BASE, _add(tarfile.LNKTYPE, "hard", "echo.py")),  # type: ignore[arg-type]
        make_tar(BASE, _add(tarfile.CHRTYPE, "dev")),  # type: ignore[arg-type]
        make_tar(BASE, _add(tarfile.FIFOTYPE, "fifo")),  # type: ignore[arg-type]
        make_tar({**BASE, "a" * 120 + "/../../x": b"evil"}, fmt=tarfile.PAX_FORMAT),
        make_tar({**BASE, "b" * 120 + "/../../x": b"evil"}, fmt=tarfile.GNU_FORMAT),
    ],
    ids=["dotdot", "nested", "absolute", "symlink", "hardlink", "device", "fifo", "pax", "gnu"],
)
def test_unsafe_rejected(tmp_path: Path, data: bytes) -> None:
    dest = tmp_path / "d"
    dest.mkdir()
    assert code_of(data, dest) == "unsafe_archive"
    assert not (tmp_path / "x").exists()


def test_duplicate_names_rejected(tmp_path: Path) -> None:
    def dup(tf: tarfile.TarFile) -> None:
        info = tarfile.TarInfo("./echo.py")
        info.size = 1
        tf.addfile(info, io.BytesIO(b"y"))

    assert code_of(make_tar(BASE, dup), tmp_path) == "unsafe_archive"


@pytest.mark.parametrize(
    "name",
    [
        ".npmrc",
        "sub/.npmrc",
        ".yarnrc",
        ".yarnrc.yml",
        ".pnpmfile.cjs",
        "pip.conf",
        "x/pip.ini",
        "uv.toml",
        ".python-version",
        ".NPMRC",
    ],
)
def test_forbidden_config_files(tmp_path: Path, name: str) -> None:
    assert code_of(make_tar({**BASE, name: b"git=./evil.sh"}), tmp_path) == "forbidden_config_file"


def test_member_size_cap(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(archive, "MAX_EXTRACT_BYTES", 4096)
    assert code_of(make_tar({**BASE, "big": b"\0" * 100_000}), tmp_path) == "unsafe_archive"


def test_pax_header_bomb_capped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(archive, "MAX_EXTRACT_BYTES", 64 * 1024)

    def bomb(tf: tarfile.TarFile) -> None:
        info = tarfile.TarInfo("c.txt")
        info.pax_headers = {"comment": "x" * 1_000_000}
        tf.addfile(info, io.BytesIO(b""))

    data = make_tar(BASE, bomb, fmt=tarfile.PAX_FORMAT)
    assert len(data) < 64 * 1024
    assert code_of(data, tmp_path) == "unsafe_archive"


def test_member_count_cap(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(archive, "MAX_MEMBERS", 3)
    files = {**BASE, "a": b"", "b": b""}
    assert code_of(make_tar(files), tmp_path) == "unsafe_archive"


def test_memory_error_is_install_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def oom(*a: object, **k: object) -> None:
        raise MemoryError

    data = make_tar(BASE)
    monkeypatch.setattr(tarfile, "open", oom)
    assert code_of(data, tmp_path) == "unsafe_archive"


def test_not_gzip(tmp_path: Path) -> None:
    assert code_of(b"not a tarball", tmp_path) == "invalid_archive"
