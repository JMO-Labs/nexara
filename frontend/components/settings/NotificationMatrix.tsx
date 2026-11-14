"use client";
/**
 * @file components/settings/NotificationMatrix.tsx
 * @brief Per-type channel/cadence matrix built from the type registry.
 */
import { useTranslations } from "next-intl";
import { Option, Select, Switch } from "@/components/ui";
import type {
  Channel,
  DigestCadence,
  NotificationTypeDescriptor,
  PreferencesPayload,
} from "@/lib/notifications/types";

const CADENCES: DigestCadence[] = ["instant", "hourly", "daily", "off"];

export interface NotificationMatrixProps {
  types: NotificationTypeDescriptor[];
  prefs: Pick<PreferencesPayload, "notification_prefs" | "digest_cadence">;
  onChannel: (type: string, channel: Channel, value: boolean) => void;
  onCadence: (type: string, cadence: DigestCadence) => void;
}

/**
 * @brief Matrix grouped by category.
 * @param props types, current prefs and change handlers
 * @return grouped rows
 */
export function NotificationMatrix({
  types,
  prefs,
  onChannel,
  onCadence,
}: NotificationMatrixProps) {
  const t = useTranslations("settings.notif");
  const tr = useTranslations();
  const groups = new Map<string, NotificationTypeDescriptor[]>();
  for (const d of types)
    groups.set(d.category, [...(groups.get(d.category) ?? []), d]);

  return (
    <div className="space-y-4">
      {[...groups].map(([category, list]) => (
        <section key={category} className="space-y-2">
          <h3 className="text-sm font-semibold capitalize">{category}</h3>
          {list.map((d) => {
            const label = tr(d.label_i18n);
            return (
              <div
                key={d.key}
                className="flex flex-wrap items-center gap-x-4 gap-y-1"
              >
                <span className="min-w-40 flex-1 text-sm">{label}</span>
                {d.user_configurable.map((ch) => {
                  const chLabel = t(`ch_${ch}`);
                  const on =
                    prefs.notification_prefs[d.key]?.[ch] ??
                    d.default_channels[ch] ??
                    false;
                  return (
                    <label
                      key={ch}
                      className="flex min-h-11 items-center gap-2 text-sm"
                    >
                      <Switch
                        aria-label={`${label} ${chLabel}`}
                        checked={on}
                        onCheckedChange={(v) => onChannel(d.key, ch, v)}
                      />
                      {chLabel}
                    </label>
                  );
                })}
                {d.digestable && (
                  <div className="w-32">
                    <Select
                      label={`${label} ${t("digest")}`}
                      value={prefs.digest_cadence[d.key] ?? "instant"}
                      onValueChange={(v) =>
                        onCadence(d.key, v as DigestCadence)
                      }
                    >
                      {CADENCES.map((c) => (
                        <Option key={c} value={c}>
                          {t(`cad_${c}`)}
                        </Option>
                      ))}
                    </Select>
                  </div>
                )}
              </div>
            );
          })}
        </section>
      ))}
    </div>
  );
}
