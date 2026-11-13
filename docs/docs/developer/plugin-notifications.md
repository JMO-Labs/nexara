# Notification types in plugins

Plugins extend the notification system by registering one or more
`NotificationType` values when their package is imported. A plugin can also
override how a type renders in the frontend and add its own delivery channel.

## Minimal example

```python
# my_plugin/notifications.py
from datetime import datetime

from app.services.notifications.registry import (
    Action,
    NotificationPayload,
    NotificationType,
    register,
)


class BookClubMeetingPayload(NotificationPayload):
    book_title: str
    meets_at: datetime


register(
    NotificationType(
        key="bookclub.meeting_reminder",
        category="plugin",
        payload_schema=BookClubMeetingPayload,
        default_channels={"inapp": True, "email": True, "push": True, "toast": True},
        bypass_dnd=False,
        actions=(
            Action(
                key="ack",
                label_i18n="bookclub.notif.ack",
                method="POST",
                url_template="/api/v1/plugins/bookclub/meetings/{target_id}/ack",
            ),
        ),
        label_i18n="bookclub.notif.meeting_reminder",
        icon="book-open",
        plugin_id="bookclub",
    )
)
```

`NotificationPayload` already provides `message`, `link`, `actor_id` and
`target_id`; subclass it to add your own fields. `register()` raises
`ValueError` if the key is already registered, so use a plugin-prefixed key.

Other `NotificationType` fields (all optional): `user_configurable`,
`group_window_seconds`, `toast_on_arrival`, `digestable`. `Action.style` is
`"primary"`, `"neutral"` (default) or `"danger"`.

Registering once gives the plugin a settings row, per-channel user
preferences, group/DnD/digest/webhook handling, and inline actions in the
bell, drawer and toast.

## Frontend renderer override

Without an override, the default renderer shows the translated
`label_i18n` as title and `payload.message` as body. To customise it,
register a renderer for the type key:

```ts
import { registerRenderer } from "@/lib/notifications/renderers";

registerRenderer("bookclub.meeting_reminder", (type, payload, t) => ({
  title: t("bookclub.notif.title"),
  body: String(payload.book_title ?? ""),
  icon: "book-open",
  link: `/plugins/bookclub/meetings/${String(payload.target_id)}`,
  actions: type.actions.map((a) => ({
    key: a.key,
    label: t(a.label_i18n),
    method: a.method,
    url: a.url_template.replace("{target_id}", String(payload.target_id)),
    style: a.style,
  })),
}));
```

The renderer signature is `RenderFn`:
`(type: NotificationTypeDescriptor, payload: Record<string, unknown>, t: Translate) => RenderedNotif`.
`Translate` takes a key only (`(key: string) => string`), with no
interpolation parameters. `RenderedNotif` has `title`, `body`, `icon`,
`link` (`string | null`) and `actions`.

## Adding a custom channel

A channel implements the `Channel` protocol from
`app.services.notifications.channels.base`: a class-level `key` and an async
`send()` that returns a `ChannelResult` and never raises.

```python
from typing import ClassVar

from app.models.notification import Notification
from app.services.notifications.channels.base import ChannelResult


class SmsChannel:
    key: ClassVar[str] = "sms"

    async def send(self, notification: Notification) -> ChannelResult:
        try:
            ...  # talk to your SMS vendor
        except Exception as exc:
            return ChannelResult(ok=False, error=str(exc))
        return ChannelResult(ok=True)
```

Register it on the process-wide dispatcher at app boot:

```python
from app.core.dependencies import get_dispatcher

get_dispatcher().register_channel(SmsChannel())
```

The dispatcher sends only to channels enabled for the notification, so
include your channel key in the type's `default_channels`. Channels are
isolated: a failure in one does not block the others.
