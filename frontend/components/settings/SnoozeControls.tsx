"use client";
/**
 * @file components/settings/SnoozeControls.tsx
 * @brief Snooze presets, custom date and clear button.
 */
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui";
import { clearSnooze, snooze } from "@/lib/api/notifications";

export const PREFS_KEY = ["notifications", "preferences"] as const;

/** @brief ISO instant for local midnight tomorrow. */
export function tomorrowIso(now = new Date()): string {
  const d = new Date(now);
  d.setDate(d.getDate() + 1);
  d.setHours(0, 0, 0, 0);
  return d.toISOString();
}

/**
 * @brief Snooze controls.
 * @param props until: current snooze end (ISO) or null
 * @return button row
 */
export function SnoozeControls({ until }: { until: string | null }) {
  const t = useTranslations("settings.notif");
  const qc = useQueryClient();
  const [custom, setCustom] = useState("");
  const done = () => qc.invalidateQueries({ queryKey: PREFS_KEY });
  const set = useMutation({
    mutationFn: (d: string) => snooze(d),
    onSuccess: done,
  });
  const clear = useMutation({
    mutationFn: () => clearSnooze(),
    onSuccess: done,
  });
  const active = until !== null && new Date(until) > new Date();

  return (
    <div className="flex flex-wrap items-center gap-2">
      <Button size="sm" variant="outline" onClick={() => set.mutate("1h")}>
        {t("snooze_1h")}
      </Button>
      <Button
        size="sm"
        variant="outline"
        onClick={() => set.mutate("until_morning")}
      >
        {t("snooze_morning")}
      </Button>
      <Button
        size="sm"
        variant="outline"
        onClick={() => set.mutate(tomorrowIso())}
      >
        {t("snooze_tomorrow")}
      </Button>
      <input
        type="datetime-local"
        aria-label={t("snooze_custom")}
        className="h-8 rounded-lg border border-current/30 bg-transparent px-2 text-sm"
        value={custom}
        onChange={(e) => setCustom(e.target.value)}
      />
      <Button
        size="sm"
        variant="outline"
        disabled={!custom}
        onClick={() => set.mutate(new Date(custom).toISOString())}
      >
        {t("snooze_apply")}
      </Button>
      {active && (
        <>
          <span className="text-sm text-muted">
            {t("snoozed_until")} {new Date(until).toLocaleString()}
          </span>
          <Button size="sm" variant="ghost" onClick={() => clear.mutate()}>
            {t("snooze_clear")}
          </Button>
        </>
      )}
    </div>
  );
}
