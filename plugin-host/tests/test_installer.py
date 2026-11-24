"""
@file
@brief Installer orchestration: sha256, extraction, manifest, deps, swap and prune.
"""

from pathlib import Path
from typing import Any

import httpx
import pytest
import respx

from host.installer import InstallError, install, prune, swap_current
from host.models import InstallSpec
from tests.conftest import PKG_IP_URL, good_tar, make_tar, manifest, spec_body

PID = "dev.nexara.echo"
Calls = list[tuple[list[str], Path, int | None]]


@pytest.fixture
def calls() -> Calls:
    return []


@pytest.fixture
def runner(calls: Calls) -> Any:
    async def run(argv: list[str], cwd: Path, uid: int | None) -> None:
        calls.append((argv, cwd, uid))

    return run


def spec(data: bytes, version: str = "1.0.0", **over: object) -> InstallSpec:
    return InstallSpec.model_validate(spec_body(data, version, **over))


async def do_install(tmp_path: Path, data: bytes, s: InstallSpec, runner: Any) -> Path:
    with respx.mock:
        respx.get(PKG_IP_URL).mock(return_value=httpx.Response(200, content=data))
        return await install(PID, s, tmp_path, runner=runner)


def pdir(tmp_path: Path) -> Path:
    return tmp_path / "plugins" / PID


async def test_install_prepares_version_dir(tmp_path: Path, runner: Any, calls: Calls) -> None:
    data = good_tar()
    root = await do_install(tmp_path, data, spec(data), runner)
    assert root == pdir(tmp_path) / "1.0.0"
    assert (root / "echo.py").read_bytes() == b"print('hi')\n"
    assert not (pdir(tmp_path) / "current").exists()  # swapped only after start
    assert [a[:2] for a, _, _ in calls] == [["uv", "venv"], ["uv", "pip"]]


async def test_sha_mismatch_extracts_nothing(tmp_path: Path, runner: Any, calls: Calls) -> None:
    data = good_tar()
    with pytest.raises(InstallError) as e:
        await do_install(tmp_path, data, spec(data, sha256="0" * 64), runner)
    assert e.value.code == "sha256_mismatch"
    assert not (pdir(tmp_path) / "1.0.0").exists()
    assert calls == []


async def test_unsafe_archive_cleaned_up(tmp_path: Path, runner: Any, calls: Calls) -> None:
    data = make_tar({"nexara-plugin.toml": manifest(), "echo.py": b"", "../x": b"evil"})
    with pytest.raises(InstallError) as e:
        await do_install(tmp_path, data, spec(data), runner)
    assert e.value.code == "unsafe_archive"
    assert not (pdir(tmp_path) / "1.0.0").exists() and not (pdir(tmp_path) / "x").exists()
    assert calls == []


async def test_forbidden_config_rejected(tmp_path: Path, runner: Any, calls: Calls) -> None:
    data = make_tar({"nexara-plugin.toml": manifest(), "echo.py": b"", ".npmrc": b"git=./e"})
    with pytest.raises(InstallError) as e:
        await do_install(tmp_path, data, spec(data), runner)
    assert e.value.code == "forbidden_config_file"
    assert calls == []


async def test_manifest_id_mismatch(tmp_path: Path, runner: Any) -> None:
    data = good_tar(plugin_id="dev.nexara.other")
    with pytest.raises(InstallError) as e:
        await do_install(tmp_path, data, spec(data), runner)
    assert e.value.code == "manifest_mismatch"
    assert not (pdir(tmp_path) / "1.0.0").exists()


async def test_missing_entrypoint(tmp_path: Path, runner: Any) -> None:
    data = make_tar({"nexara-plugin.toml": manifest()})
    with pytest.raises(InstallError) as e:
        await do_install(tmp_path, data, spec(data), runner)
    assert e.value.code == "entrypoint_missing"


async def test_update_keeps_previous_until_swap(tmp_path: Path, runner: Any) -> None:
    v1, v2 = good_tar("1.0.0"), good_tar("1.1.0")
    await do_install(tmp_path, v1, spec(v1), runner)
    swap_current(pdir(tmp_path), "1.0.0")
    root = await do_install(tmp_path, v2, spec(v2, "1.1.0"), runner)
    assert (pdir(tmp_path) / "1.0.0").is_dir()
    assert (pdir(tmp_path) / "current").resolve() == (pdir(tmp_path) / "1.0.0").resolve()
    swap_current(pdir(tmp_path), "1.1.0")
    prune(pdir(tmp_path), "1.1.0")
    assert (pdir(tmp_path) / "current").resolve() == root.resolve()
    assert not (pdir(tmp_path) / "1.0.0").exists()
    assert sorted(p.name for p in pdir(tmp_path).iterdir()) == [".cache", "1.1.0", "current"]


async def test_prune_keeps_cache(tmp_path: Path) -> None:
    p = pdir(tmp_path)
    for d in ("1.0.0", "1.1.0", ".cache/npm"):
        (p / d).mkdir(parents=True)
    swap_current(p, "1.1.0")
    prune(p, "1.1.0")
    assert sorted(x.name for x in p.iterdir()) == [".cache", "1.1.0", "current"]


async def test_failed_deps_removes_new_dir(tmp_path: Path, runner: Any) -> None:
    v1 = good_tar("1.0.0")
    await do_install(tmp_path, v1, spec(v1), runner)
    swap_current(pdir(tmp_path), "1.0.0")

    async def boom(argv: list[str], cwd: Path, uid: int | None) -> None:
        raise InstallError("deps_failed:exit=1")

    v2 = good_tar("1.1.0")
    with pytest.raises(InstallError):
        await do_install(tmp_path, v2, spec(v2, "1.1.0"), boom)
    assert (pdir(tmp_path) / "current").resolve() == (pdir(tmp_path) / "1.0.0").resolve()
    assert not (pdir(tmp_path) / "1.1.0").exists()


async def test_same_version_same_sha_skips_download(tmp_path: Path, runner: Any) -> None:
    data = good_tar()
    await do_install(tmp_path, data, spec(data), runner)
    swap_current(pdir(tmp_path), "1.0.0")
    with respx.mock(assert_all_called=False) as router:
        route = router.get(PKG_IP_URL)
        root = await install(PID, spec(data), tmp_path, runner=runner)
    assert not route.called
    assert root == pdir(tmp_path) / "1.0.0"


async def test_same_version_other_sha_conflicts(tmp_path: Path, runner: Any) -> None:
    data = good_tar()
    await do_install(tmp_path, data, spec(data), runner)
    swap_current(pdir(tmp_path), "1.0.0")
    with pytest.raises(InstallError) as e:
        await install(PID, spec(data, sha256="f" * 64), tmp_path, runner=runner)
    assert e.value.code == "version_conflict"


async def test_uid_passed_to_runner(tmp_path: Path, runner: Any, calls: Calls) -> None:
    data = good_tar()
    with respx.mock:
        respx.get(PKG_IP_URL).mock(return_value=httpx.Response(200, content=data))
        await install(PID, spec(data), tmp_path, runner=runner, uid=20007)
    assert {uid for _, _, uid in calls} == {20007}


async def test_env_not_written_to_disk(
    tmp_path: Path, runner: Any, secrets: tuple[str, ...]
) -> None:
    data = good_tar()
    await do_install(tmp_path, data, spec(data), runner)
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


@pytest.mark.parametrize("link", ["plugins", f"plugins/{PID}", f"plugins/{PID}/1.0.0"])
async def test_symlinked_plugin_path_refused_first(
    tmp_path: Path, runner: Any, calls: Calls, link: str
) -> None:
    target = tmp_path / "elsewhere"
    target.mkdir()
    path = tmp_path / link
    path.parent.mkdir(parents=True, exist_ok=True)
    path.symlink_to(target)
    data = good_tar()
    with respx.mock:
        route = respx.get(PKG_IP_URL).mock(return_value=httpx.Response(200, content=data))
        with pytest.raises(InstallError) as e:
            await install(PID, spec(data), tmp_path, runner=runner)
    assert e.value.code == "unsafe_path"
    assert not route.called and not calls
    assert list(target.iterdir()) == []
