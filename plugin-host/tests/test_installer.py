"""
@file
@brief Installer tests: download, sha256, safe extraction, deps, symlink swap.
"""

import io
import tarfile
from pathlib import Path

import httpx
import pytest
import respx

from host import installer
from host.installer import InstallError, install
from host.models import InstallSpec
from tests.conftest import PKG_URL, good_tar, make_tar, manifest, spec_body

PID = "dev.nexara.echo"


@pytest.fixture
def runs(monkeypatch: pytest.MonkeyPatch) -> list[tuple[list[str], Path]]:
    """@brief Capture installer subprocess calls instead of running npm/uv."""
    calls: list[tuple[list[str], Path]] = []

    async def fake_run(argv: list[str], cwd: Path) -> None:
        calls.append((argv, cwd))

    monkeypatch.setattr(installer, "_run", fake_run)
    return calls


def spec(data: bytes, version: str = "1.0.0", **over: object) -> InstallSpec:
    return InstallSpec.model_validate(spec_body(data, version, **over))


async def do_install(tmp_path: Path, data: bytes, s: InstallSpec) -> Path:
    with respx.mock:
        respx.get(PKG_URL).mock(return_value=httpx.Response(200, content=data))
        return await install(PID, s, tmp_path)


def plugin_dir(tmp_path: Path) -> Path:
    return tmp_path / "plugins" / PID


async def test_python_install_swaps_current(tmp_path: Path, runs: list) -> None:
    data = good_tar()
    root = await do_install(tmp_path, data, spec(data))
    assert root == plugin_dir(tmp_path) / "1.0.0"
    assert (plugin_dir(tmp_path) / "current").resolve() == root.resolve()
    assert (root / "echo.py").read_bytes() == b"print('hi')\n"
    argvs = [a for a, _ in runs]
    assert argvs[0][:2] == ["uv", "venv"]
    assert argvs[1][:3] == ["uv", "pip", "install"]
    assert "--only-binary" in argvs[1] and ":all:" in argvs[1]
    assert all(cwd == root for _, cwd in runs)


async def test_node_install_ignores_scripts(tmp_path: Path, runs: list) -> None:
    data = make_tar(
        {
            "nexara-plugin.toml": manifest(),
            "index.js": b"",
            "package.json": b"{}",
            "package-lock.json": b"{}",
        }
    )
    await do_install(tmp_path, data, spec(data, runtime="node", entrypoint="index.js"))
    assert runs[0][0] == ["npm", "ci", "--omit=dev", "--ignore-scripts"]


async def test_sha_mismatch_extracts_nothing(tmp_path: Path, runs: list) -> None:
    data = good_tar()
    with pytest.raises(InstallError) as e:
        await do_install(tmp_path, data, spec(data, sha256="0" * 64))
    assert e.value.code == "sha256_mismatch"
    assert not (plugin_dir(tmp_path) / "1.0.0").exists()
    assert runs == []


def _symlink(tf: tarfile.TarFile) -> None:
    info = tarfile.TarInfo("link")
    info.type = tarfile.SYMTYPE
    info.linkname = "/etc/passwd"
    tf.addfile(info)


def _hardlink(tf: tarfile.TarFile) -> None:
    info = tarfile.TarInfo("hard")
    info.type = tarfile.LNKTYPE
    info.linkname = "echo.py"
    tf.addfile(info)


def _device(tf: tarfile.TarFile) -> None:
    info = tarfile.TarInfo("dev")
    info.type = tarfile.CHRTYPE
    tf.addfile(info)


BASE = {"nexara-plugin.toml": manifest(), "echo.py": b""}


@pytest.mark.parametrize(
    "data",
    [
        make_tar({**BASE, "../x": b"evil"}),
        make_tar({**BASE, "a/../../x": b"evil"}),
        make_tar({**BASE, "/abs": b"evil"}),
        make_tar(BASE, _symlink),
        make_tar(BASE, _hardlink),
        make_tar(BASE, _device),
    ],
    ids=["dotdot", "nested-dotdot", "absolute", "symlink", "hardlink", "device"],
)
async def test_unsafe_archive_rejected(tmp_path: Path, runs: list, data: bytes) -> None:
    with pytest.raises(InstallError) as e:
        await do_install(tmp_path, data, spec(data))
    assert e.value.code == "unsafe_archive"
    assert not (tmp_path / "x").exists() and not (tmp_path / "plugins" / "x").exists()
    assert not (plugin_dir(tmp_path) / "1.0.0").exists()
    assert runs == []


async def test_extract_size_cap(
    tmp_path: Path, runs: list, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(installer, "MAX_EXTRACT_BYTES", 100)
    data = make_tar({**BASE, "big": b"\0" * 1000})
    with pytest.raises(InstallError) as e:
        await do_install(tmp_path, data, spec(data))
    assert e.value.code == "unsafe_archive"


async def test_download_size_cap(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(installer, "MAX_DOWNLOAD_BYTES", 10)
    data = good_tar()
    with pytest.raises(InstallError) as e:
        await do_install(tmp_path, data, spec(data))
    assert e.value.code == "package_too_large"


async def test_http_url_rejected(tmp_path: Path) -> None:
    data = good_tar()
    with pytest.raises(InstallError) as e:
        await install(PID, spec(data, package_url="http://x.example/p.tgz"), tmp_path)
    assert e.value.code == "download_failed"


async def test_redirect_to_http_rejected(tmp_path: Path) -> None:
    data = good_tar()
    with respx.mock:
        respx.get(PKG_URL).mock(
            return_value=httpx.Response(302, headers={"location": "http://x.example/p"})
        )
        with pytest.raises(InstallError) as e:
            await install(PID, spec(data), tmp_path)
    assert e.value.code == "download_failed"


async def test_manifest_id_mismatch(tmp_path: Path, runs: list) -> None:
    data = good_tar(plugin_id="dev.nexara.other")
    with pytest.raises(InstallError) as e:
        await do_install(tmp_path, data, spec(data))
    assert e.value.code == "manifest_mismatch"
    assert not (plugin_dir(tmp_path) / "1.0.0").exists()


async def test_missing_entrypoint(tmp_path: Path, runs: list) -> None:
    data = make_tar({"nexara-plugin.toml": manifest()})
    with pytest.raises(InstallError) as e:
        await do_install(tmp_path, data, spec(data))
    assert e.value.code == "entrypoint_missing"


async def test_update_keeps_previous_until_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pdir = plugin_dir(tmp_path)
    seen: list[tuple[bool, Path]] = []

    async def fake_run(argv: list[str], cwd: Path) -> None:
        seen.append(((pdir / "1.0.0").is_dir(), (pdir / "current").resolve()))

    monkeypatch.setattr(installer, "_run", fake_run)
    v1, v2 = good_tar("1.0.0"), good_tar("1.1.0")
    await do_install(tmp_path, v1, spec(v1))
    seen.clear()
    root = await do_install(tmp_path, v2, spec(v2, "1.1.0"))
    assert seen and all(old and cur == (pdir / "1.0.0").resolve() for old, cur in seen)
    assert (pdir / "current").resolve() == root.resolve() == (pdir / "1.1.0").resolve()
    assert not (pdir / "1.0.0").exists()


async def test_failed_update_keeps_current(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pdir = plugin_dir(tmp_path)

    async def ok(argv: list[str], cwd: Path) -> None:
        return None

    monkeypatch.setattr(installer, "_run", ok)
    v1 = good_tar("1.0.0")
    await do_install(tmp_path, v1, spec(v1))

    async def boom(argv: list[str], cwd: Path) -> None:
        raise InstallError("deps_failed")

    monkeypatch.setattr(installer, "_run", boom)
    v2 = good_tar("1.1.0")
    with pytest.raises(InstallError):
        await do_install(tmp_path, v2, spec(v2, "1.1.0"))
    assert (pdir / "current").resolve() == (pdir / "1.0.0").resolve()
    assert not (pdir / "1.1.0").exists()


async def test_same_version_same_sha_skips_download(tmp_path: Path, runs: list) -> None:
    data = good_tar()
    await do_install(tmp_path, data, spec(data))
    with respx.mock(assert_all_called=False) as router:
        route = router.get(PKG_URL)
        root = await install(PID, spec(data), tmp_path)
    assert not route.called
    assert root == plugin_dir(tmp_path) / "1.0.0"


async def test_env_not_written_to_disk(tmp_path: Path, runs: list, secrets: tuple) -> None:
    data = good_tar()
    await do_install(tmp_path, data, spec(data))
    for f in tmp_path.rglob("*"):
        if f.is_file():
            body = f.read_bytes()
            assert not any(s.encode() in body for s in secrets), f


def test_spec_rejects_bad_entrypoint_and_extra_env() -> None:
    data = good_tar()
    for bad in ("/etc/passwd", "../x.py", ""):
        with pytest.raises(ValueError):
            spec(data, entrypoint=bad)
    body = spec_body(data)
    body["env"]["LD_PRELOAD"] = "/x.so"
    with pytest.raises(ValueError):
        InstallSpec.model_validate(body)
    assert "SECRET" not in repr(spec(data))


def test_tar_member_helper_sanity() -> None:
    # guard: our fixture tarballs really contain what the tests think
    with tarfile.open(fileobj=io.BytesIO(make_tar(BASE, _symlink))) as tf:
        assert any(m.issym() for m in tf.getmembers())
