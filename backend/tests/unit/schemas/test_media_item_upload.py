"""
@file test_media_item_upload.py
@brief Standalone uploads (source="upload") serialize without a source_id.
"""

from datetime import UTC, datetime

from app.schemas.subgroup import MediaItemResponse


def test_upload_item_has_no_source_id() -> None:
    item = MediaItemResponse(
        media_id="m1",
        media={"id": "m1"},
        source="upload",
        source_id=None,
        created_at=datetime.now(UTC),
    )
    assert item.source_id is None
    assert item.source_title is None
