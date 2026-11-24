"use client";
/**
 * @file components/settings/NotificationsTab.tsx
 * @brief Notifications settings: snooze, quiet hours, push, matrix, webhooks.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { Skeleton } from "@/components/ui";
import { Panel } from "@/components/ui/page";
import { getPreferences, patchPreferences } from "@/lib/api/notifications";
import { useNotificationsSync } from "@/hooks/useNotificationsSync";
import { useNotificationRegistry } from "@/lib/notifications/registry";
import type {
  Channel,
  DigestCadence,
  PreferencesPayload,
} from "@/lib/notifications/types";
import { DnDScheduleEditor } from "./DnDScheduleEditor";
import { NotificationMatrix } from "./NotificationMatrix";
import { RecapSetting } from "./RecapSetting";
import { ReconnectSetting } from "./ReconnectSetting";
import { PushDevices } from "./PushDevices";
import { PREFS_KEY, SnoozeControls } from "./SnoozeControls";
import { AppriseSection } from "./AppriseSection";
import { useAppriseUrls } from "@/hooks/useAppriseUrls";
import { WebhookList } from "./WebhookList";

const DEBOUNCE_MS = 400;

/**
 * @brief Notifications tab.
 * @return stack of settings cards
 */
export function NotificationsTab() {
  const t = useTranslations("settings.notif");
  const qc = useQueryClient();
  useNotificationsSync(["user_preferences_updated"]);
  const { types } = useNotificationRegistry();
  const { data } = useQuery({ queryKey: PREFS_KEY, queryFn: getPreferences });
  const [local, setLocal] = useState<PreferencesPayload | null>(null);
  const pending = useRef<Partial<PreferencesPayload>>({});
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const { data: apps } = useAppriseUrls();
  const prefs = local ?? data ?? null;

  useEffect(() => {
    if (data) setLocal(data);
  }, [data]);
  // Flush (not drop) a pending debounced PATCH when the tab unmounts.
  useEffect(
    () => () => {
      if (timer.current) clearTimeout(timer.current);
      const body = pending.current;
      pending.current = {};
      if (Object.keys(body).length) void patchPreferences(body);
    },
    [],
  );

  /** Apply optimistically and send one merged PATCH after the debounce. */
  const change = useCallback(
    (patch: Partial<PreferencesPayload>) => {
      setLocal((cur) => (cur ? { ...cur, ...patch } : cur));
      pending.current = { ...pending.current, ...patch };
      if (timer.current) clearTimeout(timer.current);
      timer.current = setTimeout(async () => {
        const body = pending.current;
        pending.current = {};
        try {
          await patchPreferences(body);
        } finally {
          qc.invalidateQueries({ queryKey: PREFS_KEY });
        }
      }, DEBOUNCE_MS);
    },
    [qc],
  );

  if (!prefs) return <Skeleton height={200} rounded="lg" />;

  const onChannel = (type: string, ch: Channel, value: boolean) => {
    const all = pending.current.notification_prefs ?? prefs.notification_prefs;
    change({
      notification_prefs: {
        ...all,
        [type]: { ...all[type], [ch]: value },
      },
    });
  };
  const onCadence = (type: string, c: DigestCadence) =>
    change({
      digest_cadence: {
        ...(pending.current.digest_cadence ?? prefs.digest_cadence),
        [type]: c,
      },
    });

  return (
    <div className="flex flex-col gap-4">
      <Panel title={t("snooze_title")}>
        <SnoozeControls until={prefs.dnd_until} />
      </Panel>
      <Panel title={t("dnd_title")}>
        <DnDScheduleEditor
          schedule={prefs.dnd_schedule}
          timezone={prefs.dnd_timezone}
          onChange={(s, tz) => change({ dnd_schedule: s, dnd_timezone: tz })}
        />
      </Panel>
      <Panel title={t("recap_title")}>
        <RecapSetting
          value={prefs.recap_cadence ?? "weekly"}
          onChange={(c) => change({ recap_cadence: c })}
        />
      </Panel>
      <Panel title={t("reconnect_title")}>
        <ReconnectSetting
          enabled={prefs.reconnect_nudges ?? true}
          days={prefs.reconnect_days ?? 30}
          onChange={change}
        />
      </Panel>
      <PushDevices />
      <Panel title={t("matrix_title")}>
        <NotificationMatrix
          types={types}
          prefs={prefs}
          onChannel={onChannel}
          onCadence={onCadence}
          disabledChannels={
            apps && apps.length === 0
              ? { apprise: t("apprise_add_first") }
              : undefined
          }
        />
      </Panel>
      <Panel title={t("apprise_title")}>
        <AppriseSection />
      </Panel>
      <Panel title={t("webhooks_title")}>
        <WebhookList />
      </Panel>
    </div>
  );
}
