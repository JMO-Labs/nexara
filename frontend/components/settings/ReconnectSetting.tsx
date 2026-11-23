"use client";
/**
 * @file components/settings/ReconnectSetting.tsx
 * @brief Toggle and quiet-days select for private reconnect reminders.
 */
import { useTranslations } from "next-intl";
import type {
  PreferencesPayload,
  ReconnectDays,
} from "@/lib/notifications/types";

const DAYS: ReconnectDays[] = [14, 30, 60, 90];

/**
 * @brief Reconnect reminders on/off plus days of silence before a reminder.
 * @param props enabled / days: current values; onChange: partial prefs patch
 * @return labelled native checkbox and select (keyboard and AT friendly)
 */
export function ReconnectSetting({
  enabled,
  days,
  onChange,
}: {
  enabled: boolean;
  days: ReconnectDays;
  onChange: (patch: Partial<PreferencesPayload>) => void;
}) {
  const t = useTranslations("settings.notif");
  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm text-muted-foreground">{t("reconnect_hint")}</p>
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={enabled}
          onChange={(e) => onChange({ reconnect_nudges: e.target.checked })}
          className="size-4 accent-primary focus-visible:outline-2 focus-visible:outline-offset-2"
        />
        {t("reconnect_toggle")}
      </label>
      <label className="flex items-center gap-2 text-sm">
        {t("reconnect_days")}
        <select
          value={days}
          disabled={!enabled}
          onChange={(e) =>
            onChange({
              reconnect_days: Number(e.target.value) as ReconnectDays,
            })
          }
          className="rounded-md border border-border bg-background px-2 py-1 text-foreground focus-visible:outline-2 focus-visible:outline-offset-2 disabled:opacity-60"
        >
          {DAYS.map((d) => (
            <option key={d} value={d}>
              {t("reconnect_days_option", { days: d })}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}
