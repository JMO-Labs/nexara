"use client";
/**
 * @file components/settings/NotificationsTab.tsx
 * @brief Notifications settings tab with per-channel toggles.
 */
import { useCallback, useState } from "react";
import { Card, SettingsRow, Skeleton, Switch } from "@/components/ui";
import {
  useNotificationPrefs,
  useUpdateNotificationPrefs,
} from "@/hooks/useSettings";
import type { NotificationPreferences } from "@/lib/api/settings";
import { useTranslations } from "next-intl";
import { PushSubscriptionRow } from "./PushSubscriptionRow";
import { NotificationDigestRow } from "./NotificationDigestRow";
import { AppriseList, useAppriseUrls } from "./AppriseList";

const NOTIF_TYPES = [
  { key: "mention", label: "Mention" },
  { key: "comment", label: "Comment" },
  { key: "reaction", label: "Reaction" },
  { key: "new_post", label: "New post" },
  { key: "system", label: "System" },
  { key: "invite_accepted", label: "Invite accepted" },
  { key: "event_reminder", label: "Event reminder" },
  { key: "event_rsvp", label: "Event RSVP" },
  { key: "gallery_activity", label: "Gallery activity" },
  { key: "prompt", label: "Prompt" },
  { key: "prompt_summary", label: "Prompt summary" },
  { key: "poll", label: "Poll" },
  { key: "dm", label: "Direct message" },
  { key: "birthday", label: "Birthday" },
];

const CHANNELS = [
  { suffix: "inapp", label: "In-app" },
  { suffix: "email", label: "Email" },
  { suffix: "push", label: "Push" },
] as const;

/**
 * @brief Notification preference toggles.
 * @return notifications tab content
 */
export function NotificationsTab() {
  const { data: prefs, isLoading } = useNotificationPrefs();
  const { mutate } = useUpdateNotificationPrefs();
  const t = useTranslations("settings.apprise");
  const { data: apprise = [] } = useAppriseUrls();
  const hasApprise = apprise.some((u) => u.enabled);
  const [debounceTimer, setDebounceTimer] = useState<NodeJS.Timeout | null>(
    null,
  );

  const handleToggle = useCallback(
    (key: keyof NotificationPreferences, value: boolean | number) => {
      if (debounceTimer) clearTimeout(debounceTimer);
      const timer = setTimeout(() => {
        mutate({ [key]: value } as Partial<NotificationPreferences>);
      }, 400);
      setDebounceTimer(timer);
    },
    [debounceTimer, mutate],
  );

  const channels = hasApprise
    ? [...CHANNELS, { suffix: "apprise", label: t("matrix") }]
    : CHANNELS;

  if (isLoading) {
    return <Skeleton height={200} rounded="lg" />;
  }

  if (!prefs) {
    return (
      <p className="text-sm text-muted">No notification preferences loaded.</p>
    );
  }

  return (
    <div className="space-y-6">
      <PushSubscriptionRow />

      <Card className="max-w-3xl p-4 md:p-6">
        <h2 className="mb-2 text-lg font-semibold">Notification preferences</h2>

        {NOTIF_TYPES.map(({ key, label }) => (
          <SettingsRow
            key={key}
            label={label}
            description="Receive notifications via these channels."
          >
            <div className="flex flex-col gap-2 sm:flex-row sm:gap-6">
              {channels.map(({ suffix, label: channel }) => {
                const k =
                  `notif_${key}_${suffix}` as keyof NotificationPreferences;
                return (
                  <label
                    key={suffix}
                    className="flex min-h-11 flex-1 items-center gap-2 text-sm"
                  >
                    <Switch
                      aria-label={`${label} ${channel}`}
                      checked={Boolean(prefs[k])}
                      onCheckedChange={(v) => handleToggle(k, v)}
                    />
                    {channel}
                  </label>
                );
              })}
            </div>
          </SettingsRow>
        ))}

        <SettingsRow
          label="Mute all email"
          description="Disable all email notifications at once."
        >
          <Switch
            aria-label="Mute all email"
            checked={prefs.mute_all_email}
            onCheckedChange={(v) => handleToggle("mute_all_email", v)}
          />
        </SettingsRow>

        <SettingsRow
          label="Mute all push"
          description="Disable all push notifications at once."
        >
          <Switch
            aria-label="Mute all push"
            checked={prefs.mute_all_push}
            onCheckedChange={(v) => handleToggle("mute_all_push", v)}
          />
        </SettingsRow>

        <NotificationDigestRow
          enabled={prefs.email_digest_enabled}
          hour={prefs.email_digest_hour}
          onChange={handleToggle}
        />
      </Card>

      <Card className="max-w-3xl p-4 md:p-6">
        <h2 className="mb-2 text-lg font-semibold">{t("title")}</h2>
        <AppriseList />
      </Card>
    </div>
  );
}
