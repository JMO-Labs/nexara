"""
@file test_media_tasks.py
@brief Unit tests for media processing tasks.
"""

from app.tasks.media_tasks import delete_orphaned_media, generate_thumbnail, transcode_video


class TestGenerateThumbnail:
    """@brief Verify thumbnail generation task configuration."""

    def test_task_name(self):
        assert generate_thumbnail.name == "app.tasks.media_tasks.generate_thumbnail"

    def test_queue_is_media(self):
        assert generate_thumbnail.queue == "media"

    def test_time_limit(self):
        assert generate_thumbnail.time_limit == 300

    def test_returns_processed_status(self):
        result = generate_thumbnail("fake-media-id")
        assert result["status"] == "processed"


class TestTranscodeVideo:
    """@brief Verify video transcoding task configuration."""

    def test_task_name(self):
        assert transcode_video.name == "app.tasks.media_tasks.transcode_video"

    def test_time_limit(self):
        assert transcode_video.time_limit == 3600


class TestDeleteOrphanedMedia:
    """@brief Verify orphaned media cleanup task."""

    def test_task_name(self):
        assert delete_orphaned_media.name == "app.tasks.media_tasks.delete_orphaned_media"

    def test_returns_count(self):
        result = delete_orphaned_media()
        assert "deleted_count" in result
