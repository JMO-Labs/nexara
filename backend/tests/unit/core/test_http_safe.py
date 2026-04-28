import pytest
from app.core.http_safe import safe_fetch, UnsafeUrlError


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/",
        "http://localhost/",
        "http://10.0.0.1/",
        "http://169.254.169.254/",
        "file:///etc/passwd",
        "ftp://x/",
    ],
)
async def test_blocks_unsafe(url: str) -> None:
    with pytest.raises(UnsafeUrlError):
        await safe_fetch(url)
