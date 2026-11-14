"use client";
/**
 * @file components/settings/NotificationsTab.tsx
 * @brief Notifications settings: snooze, quiet hours, push, matrix, webhooks.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { Card, Skeleton } from "@/components/ui";
import { getPreferences, patchPreferences } from "@/lib/api/notifications";
import { useNotificationRegistry } from "@/lib/notifications/registry";
import type {
  Channel,
  DigestCadence,
  PreferencesPayload,
} from "@/lib/notifications/types";
import { DnDScheduleEditor } from "./DnDScheduleEditor";
import { NotificationMatrix } from "./NotificationMatrix";
import { PushSubscriptionRow } from "./PushSubscriptionRow";
import { PREFS_KEY, SnoozeControls } from "./SnoozeControls";
import { WebhookList } from "./WebhookList";

const DEBOUNCE_MS = 400;
const cardCls = "max-w-3xl p-4 md:p-6";

/**
 * @brief Notifications tab.
 * @return stack of settings cards
 */
export function NotificationsTab() {
  const t = useTranslations("settings.notif");
  const qc = useQueryClient();
  const { types } = useNotificationRegistry();
  const { data } = useQuery({ queryKey: PREFS_KEY, queryFn: getPreferences });
  const [local, setLocal] = useState<PreferencesPayload | null>(null);
  const pending = useRef<Partial<PreferencesPayload>>({});
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
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
    <div className="space-y-6">
      <Card className={cardCls}>
        <h2 className="mb-2 text-lg font-semibold">{t("snooze_title")}</h2>
        <SnoozeControls until={prefs.dnd_until} />
      </Card>
      <Card className={cardCls}>
        <h2 className="mb-2 text-lg font-semibold">{t("dnd_title")}</h2>
        <DnDScheduleEditor
          schedule={prefs.dnd_schedule}
          timezone={prefs.dnd_timezone}
          onChange={(s, tz) => change({ dnd_schedule: s, dnd_timezone: tz })}
        />
      </Card>
      <PushSubscriptionRow />
      <Card className={cardCls}>
        <h2 className="mb-2 text-lg font-semibold">{t("matrix_title")}</h2>
        <NotificationMatrix
          types={types}
          prefs={prefs}
          onChannel={onChannel}
          onCadence={onCadence}
        />
      </Card>
      <Card className={cardCls}>
        <h2 className="mb-2 text-lg font-semibold">{t("webhooks_title")}</h2>
        <WebhookList />
      </Card>
    </div>
  );
}
