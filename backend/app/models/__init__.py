"""
@file __init__.py
@brief SQLAlchemy model registry.

Importing this module ensures all models are registered with Base.metadata,
which Alembic needs for autogenerate to detect all tables.
"""

from app.models.activity_event import ActivityEvent  # noqa: F401
from app.models.audit import AuditLog  # noqa: F401
from app.models.auth import MagicLinkToken, RefreshToken, UserBackupCode  # noqa: F401
from app.models.bookmark import Bookmark  # noqa: F401
from app.models.branding import CommunityBranding  # noqa: F401
from app.models.calendar import Calendar  # noqa: F401
from app.models.calendar_token import CalendarToken  # noqa: F401
from app.models.chat import ChatMessage  # noqa: F401
from app.models.community import Community  # noqa: F401
from app.models.device_token import DeviceToken  # noqa: F401
from app.models.event import CalendarSubscription, Event, EventAttendance  # noqa: F401
from app.models.gallery import Gallery, GalleryCollaborator, GalleryItem  # noqa: F401
from app.models.interest import InterestCategory, UserInterest  # noqa: F401
from app.models.invite import Invite  # noqa: F401
from app.models.link_preview import (  # noqa: F401
    ChatMessageLinkPreview,
    LinkPreview,
    PostLinkPreview,
)
from app.models.list import (  # noqa: F401
    List,
    ListItem,
    ListItemCompletion,
    ListItemSignup,
    ListMember,
)
from app.models.list_template import (  # noqa: F401
    ListTemplate,
    ListTemplateField,
    ListTemplateItem,
)
from app.models.media import Media  # noqa: F401
from app.models.media_ai import MediaAIMetadata  # noqa: F401
from app.models.moderation import ContentReport, UserBlock  # noqa: F401
from app.models.notification import Notification, PushSubscription  # noqa: F401
from app.models.notification_digest import NotificationDigestQueue  # noqa: F401
from app.models.nudge import Nudge  # noqa: F401
from app.models.oauth_provider import OAuthProvider  # noqa: F401
from app.models.plugin import Plugin, PluginData  # noqa: F401
from app.models.poll import Poll, PollOption, PollVote  # noqa: F401
from app.models.post import Comment, Post, PostMedia, Reaction  # noqa: F401
from app.models.prompt import Prompt, PromptPost  # noqa: F401
from app.models.retention import RetentionPolicy, StorageAlert, StorageSnapshot  # noqa: F401
from app.models.subgroup import ChatChannel, Subgroup, SubgroupMember  # noqa: F401
from app.models.suggestion import Suggestion  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.user_export import UserExport  # noqa: F401
from app.models.user_oauth_link import UserOAuthLink  # noqa: F401
from app.models.user_settings import UserSettings  # noqa: F401
