"use client";
/**
 * @file components/settings/DnDScheduleEditor.tsx
 * @brief Weekly quiet-hours grid with multiple windows per day and a TZ picker.
 */
import { useMemo } from "react";
import { useTranslations } from "next-intl";
import { Plus, Trash2 } from "lucide-react";
import { IconButton } from "@/components/ui";

export type DndWindow = { start: string; end: string };
export type DndSchedule = Record<string, DndWindow[]>;

const DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"] as const;
const DEFAULT_WINDOW: DndWindow = { start: "22:00", end: "07:00" };
const timeCls = "h-10 rounded-lg border border-current/30 bg-transparent px-2";

export interface DnDScheduleEditorProps {
  schedule: DndSchedule | null;
  timezone: string;
  onChange: (schedule: DndSchedule | null, timezone: string) => void;
}

/** @brief IANA zone list (falls back to the current zone). */
function useZones(current: string): string[] {
  return useMemo(() => {
    const fn = (Intl as { supportedValuesOf?: (k: string) => string[] })
      .supportedValuesOf;
    const zones = fn ? fn("timeZone") : [];
    return zones.includes(current) ? zones : [current, ...zones];
  }, [current]);
}

/**
 * @brief Quiet-hours editor.
 * @param props schedule, timezone, onChange(schedule, tz)
 * @return weekly grid
 */
export function DnDScheduleEditor({
  schedule,
  timezone,
  onChange,
}: DnDScheduleEditorProps) {
  const t = useTranslations("settings.notif");
  const zones = useZones(timezone);

  const setDay = (day: string, windows: DndWindow[]) => {
    const next: DndSchedule = { ...(schedule ?? {}) };
    if (windows.length) next[day] = windows;
    else delete next[day];
    onChange(Object.keys(next).length ? next : null, timezone);
  };

  return (
    <div className="space-y-3">
      <label className="flex flex-col gap-1 text-sm sm:max-w-xs">
        {t("timezone")}
        <select
          aria-label={t("timezone")}
          className={timeCls}
          value={timezone}
          onChange={(e) => onChange(schedule, e.target.value)}
        >
          {zones.map((z) => (
            <option key={z} value={z}>
              {z}
            </option>
          ))}
        </select>
      </label>
      {DAYS.map((day) => {
        const label = t(`day_${day}`);
        const windows = schedule?.[day] ?? [];
        const edit = (i: number, patch: Partial<DndWindow>) =>
          setDay(
            day,
            windows.map((w, j) => (j === i ? { ...w, ...patch } : w)),
          );
        return (
          <div
            key={day}
            role="group"
            aria-label={label}
            className="flex flex-wrap items-center gap-2"
          >
            <span className="w-12 text-sm font-medium">{label}</span>
            {windows.map((w, i) => (
              <div key={i} className="flex items-center gap-1">
                <input
                  type="time"
                  aria-label={`${t("start")} ${label}`}
                  className={timeCls}
                  value={w.start}
                  onChange={(e) => edit(i, { start: e.target.value })}
                />
                <span aria-hidden>–</span>
                <input
                  type="time"
                  aria-label={`${t("end")} ${label}`}
                  className={timeCls}
                  value={w.end}
                  onChange={(e) => edit(i, { end: e.target.value })}
                />
                <IconButton
                  aria-label={`${t("remove_window")} ${label}`}
                  onClick={() =>
                    setDay(
                      day,
                      windows.filter((_, j) => j !== i),
                    )
                  }
                >
                  <Trash2 className="size-4" />
                </IconButton>
              </div>
            ))}
            <IconButton
              aria-label={`${t("add_window")} ${label}`}
              onClick={() => setDay(day, [...windows, DEFAULT_WINDOW])}
            >
              <Plus className="size-4" />
            </IconButton>
          </div>
        );
      })}
    </div>
  );
}
