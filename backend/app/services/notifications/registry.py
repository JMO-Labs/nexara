"""@file In-process NotificationType registry.

@brief Core primitives: payload model, Action, NotificationType and the
module-level registry with register/get/iter_types/to_json_schema.
"""

from dataclasses import asdict, dataclass
from typing import Any, Literal

from pydantic import BaseModel

Channel = Literal["inapp", "email", "push", "apprise", "webhook", "toast"]
Category = Literal["social", "event", "gallery", "prompt", "system", "plugin", "list"]


class NotificationPayload(BaseModel):
    """@brief Base payload carried by every notification."""

    message: str
    link: str | None = None
    actor_id: str | None = None
    target_id: str | None = None


@dataclass(frozen=True)
class Action:
    """@brief A user-invokable action attached to a notification."""

    key: str
    label_i18n: str
    method: Literal["POST", "PUT", "DELETE"]
    url_template: str
    style: Literal["primary", "neutral", "danger"] = "neutral"


@dataclass(frozen=True)
class NotificationType:
    """@brief Immutable description of a notification type."""

    key: str
    category: Category
    payload_schema: type[NotificationPayload]
    default_channels: dict[Channel, bool]
    user_configurable: tuple[Channel, ...] = ("inapp", "email", "push", "toast", "apprise")
    group_window_seconds: int | None = None
    toast_on_arrival: bool = False
    bypass_dnd: bool = False
    digestable: bool = True
    actions: tuple[Action, ...] = ()
    label_i18n: str = ""
    icon: str = "inbox"
    plugin_id: str | None = None


_REGISTRY: dict[str, NotificationType] = {}


def register(t: NotificationType) -> None:
    """@brief Register a type.

    @param t The type to add.
    @raises ValueError if the key is already registered.
    """
    if t.key in _REGISTRY:
        raise ValueError(f"NotificationType already registered: {t.key}")
    _REGISTRY[t.key] = t


def get(key: str) -> NotificationType:
    """@brief Look up a type by key.

    @raises KeyError if unknown.
    """
    return _REGISTRY[key]


def iter_types() -> list[NotificationType]:
    """@return All registered types in registration order."""
    return list(_REGISTRY.values())


def to_json_schema() -> list[dict[str, Any]]:
    """@return JSON-serialisable description of every registered type."""
    out: list[dict[str, Any]] = []
    for t in _REGISTRY.values():
        d = asdict(t)
        d["payload_schema"] = t.payload_schema.model_json_schema()
        d["user_configurable"] = list(t.user_configurable)
        d["actions"] = [asdict(a) for a in t.actions]
        out.append(d)
    return out
