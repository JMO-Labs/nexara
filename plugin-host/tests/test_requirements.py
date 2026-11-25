"""
@file
@brief Strict requirements.txt parser tests (exact pins only, canonical output).
"""

from pathlib import Path

import pytest

from host.deps import check_requirements
from host.installer import InstallError

H = "a" * 64
REVIEWER_PAYLOAD = (
    "six==1.16.0 # a \\\n"
    "--extra-index-url http://127.0.0.1:18765/P4/simple\n"
    "six==1.16.0 # b \\\n"
    "-r /etc/hostname\n"
)


@pytest.mark.parametrize(
    "text",
    [
        "httpx==0.28.1\n",
        "# c\n\nhttpx==0.28.1  # pinned\nanyio==4.6.2\n",
        f"httpx==0.28.1 --hash=sha256:{H}\n",
        f"httpx==0.28.1 --hash=sha256:{H} --hash=sha256:{'b' * 64}\n",
        "uvicorn[standard]==0.32.0\n",
        'uvloop==0.21.0 ; sys_platform != "win32"\n',
        'x==1.0.0; python_version >= "3.10" and platform_machine == "x86_64"\n',
        "Zope.Interface_x==7.1rc1\n",
    ],
)
def test_requirements_ok(tmp_path: Path, text: str) -> None:
    (tmp_path / "requirements.txt").write_text(text)
    check_requirements(tmp_path)


@pytest.mark.parametrize(
    "text",
    [
        "-r /proc/1/environ\n",
        "--index-url http://127.0.0.1:9/simple\nx==1.0\n",
        "-e git+https://x/y\n",
        "x @ https://evil/x.whl\n",
        "./local.whl\n",
        "/etc/hostname\n",
        "httpx\n",
        "httpx>=0.28\n",
        "httpx==0.*\n",
        "httpx==${SECRET}\n",
        "x==1.0 --extra-index-url https://e\n",
        "x==1.0 --hash=md5:abc\n",
        'x==1.0; os.system("id")\n',
        "x==1.0 \\\n-r other.txt\n",
        REVIEWER_PAYLOAD,
        f"httpx==0.28.1 \\\n    --hash=sha256:{H}\n",
        "httpx==0.28.1 # trailing \\\n",
        "httpx==0.28.1\\\n",
    ],
)
def test_requirements_unsafe(tmp_path: Path, text: str) -> None:
    (tmp_path / "requirements.txt").write_text(text)
    with pytest.raises(InstallError) as e:
        check_requirements(tmp_path)
    assert e.value.code == "requirements_unsafe"


def test_requirements_canonical(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text(
        f"# top\n\nhttpx==0.28.1   --hash=sha256:{H}  # c\n"
        f'x==1.0 ;  sys_platform != "win32" --hash=sha256:{H}\n'
    )
    assert check_requirements(tmp_path) == [
        f"httpx==0.28.1 --hash=sha256:{H}",
        f'x==1.0 ; sys_platform != "win32" --hash=sha256:{H}',
    ]


def test_requirements_mixed_hashes_rejected(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text(f"a==1.0 --hash=sha256:{H}\nb==1.0\n")
    with pytest.raises(InstallError) as e:
        check_requirements(tmp_path)
    assert e.value.code == "requirements_unsafe"
