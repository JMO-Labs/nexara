"""@file test_amazon_admin.py @brief Admin Amazon settings: secret write-only + encrypted."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.core.config import Settings
from app.services.shop.amazon_admin_service import AmazonAdminService

COLS = ("amazon_client_id", "amazon_client_secret", "amazon_partner_tag", "amazon_marketplace")


def _svc():
    row = SimpleNamespace(**dict.fromkeys(COLS))

    async def update(_cid, values):
        for k, v in values.items():
            setattr(row, k, v)
        return row

    repo = AsyncMock()
    repo.get.return_value = row
    repo.update_amazon.side_effect = update
    audit = AsyncMock()
    return AmazonAdminService(repo, uuid.uuid4(), Settings(), audit), row, audit


async def test_secret_encrypted_never_returned_and_not_audited():
    svc, row, audit = _svc()
    out = await svc.update({"client_id": "cid", "client_secret": "s3cret", "partner_tag": "fam-20"})
    assert row.amazon_client_secret and "s3cret" not in row.amazon_client_secret
    assert "s3cret" not in str(out) and out["has_secret"] and out["source"] == "admin"
    assert "s3cret" not in str(audit.append.await_args)
    out = await svc.update({"partner_tag": ""})  # omitted secret kept, '' clears
    assert out["has_secret"] and out["partner_tag"] == "" and out["source"] is None


async def test_test_reports_missing_and_bad_credentials():
    svc, _row, _a = _svc()
    assert (await svc.test())["success"] is False
    await svc.update({"client_id": "c", "client_secret": "s", "partner_tag": "t-20"})
    with (
        patch("app.services.shop.amazon.lookup", AsyncMock(return_value={"X": 1})),
        patch("app.services.shop.amazon.access_token", AsyncMock(return_value="tok")),
    ):
        assert (await svc.test())["success"] is True
