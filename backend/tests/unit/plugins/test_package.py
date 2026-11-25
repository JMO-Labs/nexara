"""
@file test_package.py
@brief Package download, sha256 check and in-memory manifest read (no extraction).
"""

from __future__ import annotations

import hashlib
import io
import tarfile
from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import AppError
from app.plugins import package
from app.plugins.package import fetch_package_manifest, read_manifest_from_tar

TOML = """
[plugin]
id = "dev.example.echo"
name = "Echo"
version = "1.0.0"
runtime = "node"
entrypoint = "index.js"
[bot]
display_name = "Echo Bot"
username = "echo"
"""


def _tar(files: dict[str, bytes], symlink: str | None = None) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for name, data in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))
        if symlink:
            info = tarfile.TarInfo(symlink)
            info.type = tarfile.SYMTYPE
            info.linkname = "/etc/passwd"
            tf.addfile(info)
    return buf.getvalue()


@pytest.fixture(autouse=True)
def _clear_cache():
    package._cache.clear()
    yield
    package._cache.clear()


def _fetch(data: bytes):
    return patch("app.plugins.package.safe_fetch", AsyncMock(return_value=data))


async def test_reads_manifest_after_sha_check():
    data = _tar({"index.js": b"x", "./nexara-plugin.toml": TOML.encode()})
    with _fetch(data):
        m = await fetch_package_manifest(
            "https://x.test/p.tgz", hashlib.sha256(data).hexdigest().upper()
        )
    assert (m.id, m.version, m.runtime) == ("dev.example.echo", "1.0.0", "node")


async def test_sha_mismatch():
    data = _tar({"nexara-plugin.toml": TOML.encode()})
    with _fetch(data), pytest.raises(AppError) as e:
        await fetch_package_manifest("https://x.test/p.tgz", "0" * 64)
    assert (e.value.code, e.value.status_code) == ("package_sha256_mismatch", 422)


async def test_bad_sha_format_rejected_before_download():
    f = AsyncMock()
    with patch("app.plugins.package.safe_fetch", f), pytest.raises(AppError) as e:
        await fetch_package_manifest("https://x.test/p.tgz", "abc")
    assert e.value.code == "invalid_sha256"
    f.assert_not_called()


async def test_http_rejected():
    with pytest.raises(AppError) as e:
        await fetch_package_manifest("http://x.test/p.tgz", "0" * 64)
    assert e.value.code == "package_url_invalid"


async def test_too_large():
    with patch("app.plugins.package.MAX_PACKAGE_BYTES", 10), _fetch(b"x" * 11):
        with pytest.raises(AppError) as e:
            await fetch_package_manifest("https://x.test/p.tgz", "0" * 64)
    assert e.value.code == "package_too_large"


def test_manifest_must_be_at_root():
    with pytest.raises(AppError) as e:
        read_manifest_from_tar(_tar({"sub/nexara-plugin.toml": TOML.encode()}))
    assert e.value.code == "invalid_manifest"


def test_symlink_manifest_rejected():
    with pytest.raises(AppError) as e:
        read_manifest_from_tar(_tar({}, symlink="nexara-plugin.toml"))
    assert e.value.code == "invalid_manifest"


def test_oversized_manifest_rejected():
    with pytest.raises(AppError) as e:
        read_manifest_from_tar(_tar({"nexara-plugin.toml": b"#" * (65 * 1024)}))
    assert e.value.code == "invalid_manifest"


def test_not_a_tar():
    with pytest.raises(AppError) as e:
        read_manifest_from_tar(b"not a tarball at all")
    assert e.value.code == "invalid_manifest"


def _bomb(fmt: int, name_len: int) -> bytes:
    """@brief .tgz whose only member has a ``name_len``-byte name (GNU long-name / PAX)."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz", format=fmt) as tf:
        info = tarfile.TarInfo("a" * name_len)
        info.size = 0
        tf.addfile(info, io.BytesIO(b""))
        info = tarfile.TarInfo("nexara-plugin.toml")
        info.size = len(TOML)
        tf.addfile(info, io.BytesIO(TOML.encode()))
    return buf.getvalue()


@pytest.mark.parametrize("fmt", [tarfile.GNU_FORMAT, tarfile.PAX_FORMAT])
def test_long_name_header_bomb_rejected(fmt):
    data = _bomb(fmt, 8 * 1024 * 1024)  # 8 MiB name compresses to a few KB
    assert len(data) < 100_000
    with pytest.raises(AppError) as e:
        read_manifest_from_tar(data)
    assert e.value.code == "invalid_manifest"
    assert "unsafe" in e.value.details["errors"][0]


def test_small_long_name_is_fine():
    assert "dev.example.echo" in read_manifest_from_tar(_bomb(tarfile.GNU_FORMAT, 300))


def test_decompressed_cap(monkeypatch):
    monkeypatch.setattr(package, "MAX_WALK_BYTES", 64 * 1024)
    data = _tar({"big.bin": b"\0" * (256 * 1024), "nexara-plugin.toml": TOML.encode()})
    with pytest.raises(AppError) as e:
        read_manifest_from_tar(data)
    assert "unsafe" in e.value.details["errors"][0]


def test_hardlink_manifest_rejected():
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        info = tarfile.TarInfo("real.toml")
        info.size = len(TOML)
        tf.addfile(info, io.BytesIO(TOML.encode()))
        link = tarfile.TarInfo("nexara-plugin.toml")
        link.type = tarfile.LNKTYPE
        link.linkname = "real.toml"
        tf.addfile(link)
    with pytest.raises(AppError) as e:
        read_manifest_from_tar(buf.getvalue())
    assert e.value.code == "invalid_manifest"


def test_plain_tar_rejected():
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tf:
        info = tarfile.TarInfo("nexara-plugin.toml")
        info.size = len(TOML)
        tf.addfile(info, io.BytesIO(TOML.encode()))
    with pytest.raises(AppError):
        read_manifest_from_tar(buf.getvalue())


async def test_review_round_trip_downloads_once():
    data = _tar({"nexara-plugin.toml": TOML.encode()})
    sha = hashlib.sha256(data).hexdigest()
    f = AsyncMock(return_value=data)
    with patch("app.plugins.package.safe_fetch", f):
        await fetch_package_manifest("https://x.test/p.tgz", sha)
        m = await fetch_package_manifest("https://x.test/p.tgz", sha.upper())
    assert m.id == "dev.example.echo" and f.await_count == 1


def _pax_record(key: str, value: str) -> bytes:
    body = f" {key}={value}\n".encode()
    n = len(body) + 1
    while len(str(n)) + len(body) != n:
        n += 1
    return str(n).encode() + body


def _raw_member(name: str, typ: bytes, data: bytes) -> bytes:
    info = tarfile.TarInfo(name)
    info.type = typ
    info.size = len(data)
    pad = (-len(data)) % tarfile.BLOCKSIZE
    return info.tobuf(format=tarfile.USTAR_FORMAT) + data + b"\0" * pad


def _raw_tgz(*parts: bytes) -> bytes:
    import gzip

    return gzip.compress(b"".join(parts) + b"\0" * (tarfile.BLOCKSIZE * 2))


def _manifest_member() -> bytes:
    return _raw_member("nexara-plugin.toml", tarfile.REGTYPE, TOML.encode())


@pytest.mark.parametrize(
    "ext",
    [
        lambda: _raw_member("pax", tarfile.XHDTYPE, _pax_record("comment", "x")),
        lambda: _raw_member("././@LongLink", tarfile.GNUTYPE_LONGNAME, b"name\0"),
    ],
)
def test_chained_extended_headers_rejected(ext):
    """@brief 5,000 small chained x / L headers used to raise RecursionError (500)."""
    one = ext()
    data = _raw_tgz(one * 5000, _manifest_member())
    with pytest.raises(AppError) as e:
        read_manifest_from_tar(data)
    assert e.value.code == "invalid_manifest"


def test_short_extended_chain_ok():
    pax = _raw_member("pax", tarfile.XHDTYPE, _pax_record("comment", "x"))
    assert "dev.example.echo" in read_manifest_from_tar(_raw_tgz(pax * 2, _manifest_member()))


def test_pax_sparse_10_rejected():
    """@brief GNU sparse 1.0 map in member data used to cost ~280 MB + ValueError."""
    pax = b"".join(
        _pax_record(k, v)
        for k, v in [
            ("GNU.sparse.major", "1"),
            ("GNU.sparse.minor", "0"),
            ("GNU.sparse.name", "nexara-plugin.toml"),
            ("GNU.sparse.realsize", "10"),
        ]
    )
    sparse_map = b"99999999\n" + b"0\n1\n" * 20000
    data = _raw_tgz(
        _raw_member("pax", tarfile.XHDTYPE, pax),
        _raw_member("GNUSparseFile.0/x", tarfile.REGTYPE, sparse_map),
    )
    with pytest.raises(AppError) as e:
        read_manifest_from_tar(data)
    assert "unsafe" in e.value.details["errors"][0]


@pytest.mark.parametrize("key", ["GNU.sparse.map", "GNU.sparse.size", "GNU.sparse.name"])
def test_any_pax_sparse_key_rejected(key):
    pax = _raw_member("pax", tarfile.XHDTYPE, _pax_record(key, "0"))
    with pytest.raises(AppError) as e:
        read_manifest_from_tar(_raw_tgz(pax, _manifest_member()))
    assert "unsafe" in e.value.details["errors"][0]


def test_gnu_sparse_member_rejected():
    data = _raw_tgz(_raw_member("s.bin", tarfile.GNUTYPE_SPARSE, b""), _manifest_member())
    with pytest.raises(AppError) as e:
        read_manifest_from_tar(data)
    assert e.value.code == "invalid_manifest"
