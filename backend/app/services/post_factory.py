"""
@file post_factory.py
@brief Build a fully wired PostService outside a request (Celery tasks)
       and for the posts router.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.dependencies import get_dispatcher
from app.repositories.comment_repo import CommentRepository, ReactionRepository
from app.repositories.interest_repo import InterestCategoryRepository, InterestRepository
from app.repositories.media_repo import MediaRepository
from app.repositories.notification_repo import NotificationRepository
from app.repositories.poll_repo import PollRepository
from app.repositories.post_repo import PostRepository
from app.repositories.prompt_repo import PromptRepository
from app.repositories.settings_repo import SettingsRepository
from app.repositories.user_repo import UserRepository
from app.services.interest_service import InterestService
from app.services.media_service import MediaService
from app.services.notification_service import NotificationService
from app.services.poll_service import PollService
from app.services.post_service import PostService
from app.services.realtime.event_bus import event_bus
from app.services.storage.factory import get_storage_backend


def build_media_service(
    db: AsyncSession,
    community_id: uuid.UUID,
    settings: Settings,
) -> MediaService:
    """@brief Build MediaService for post media attachment."""
    return MediaService(
        media_repo=MediaRepository(db),
        storage_backend=get_storage_backend(settings),
        user_repo=UserRepository(db),
        community_id=community_id,
    )


def build_post_service(
    db: AsyncSession, community_id: uuid.UUID, settings: Settings
) -> PostService:
    """@brief Build PostService with all dependencies injected."""
    notification_svc = NotificationService(
        notification_repo=NotificationRepository(db),
        settings_repo=SettingsRepository(db),
        community_id=community_id,
        dispatcher=get_dispatcher(),
    )
    media_svc = build_media_service(db, community_id, settings)
    poll_svc = PollService(
        poll_repo=PollRepository(db),
        community_id=community_id,
        event_bus=event_bus,
    )
    interest_svc = InterestService(
        interest_repo=InterestRepository(db),
        category_repo=InterestCategoryRepository(db),
        community_id=community_id,
    )

    return PostService(
        post_repo=PostRepository(db),
        comment_repo=CommentRepository(db),
        reaction_repo=ReactionRepository(db),
        notification_service=notification_svc,
        community_id=community_id,
        event_bus=event_bus,
        media_attacher=media_svc.attach_to_post,
        poll_service=poll_svc,
        prompt_repo=PromptRepository(db),
        interest_service=interest_svc,
    )
