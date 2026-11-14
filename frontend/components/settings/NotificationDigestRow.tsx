"use client";
/**
 * @file components/settings/NotificationDigestRow.tsx
 * @brief Email digest switch and hour-of-day select.
 */
import { Option, Select, SettingsRow, Switch } from "@/components/ui";
import type { NotificationPreferences } from "@/lib/api/settings";

const HOURS = Array.from({ length: 24 }, (_, h) => h);

interface Props {
  enabled: boolean;
  hour: number;
  onChange: (
    key: keyof NotificationPreferences,
    value: boolean | number,
  ) => void;
}

/**
 * @brief Digest controls; hour select is disabled while digest is off.
 * @param props current values and change callback
 * @return settings rows
 */
export function NotificationDigestRow({ enabled, hour, onChange }: Props) {
  return (
    <>
      <SettingsRow
        label="Email digest"
        description="Receive a daily summary email instead of individual ones."
      >
        <Switch
          aria-label="Email digest"
          checked={enabled}
          onCheckedChange={(v) => onChange("email_digest_enabled", v)}
        />
      </SettingsRow>
      <SettingsRow
        label="Digest hour"
        description="Hour of day to send (0-23)."
      >
        <Select
          label="Digest hour"
          value={String(hour)}
          onValueChange={(v) => onChange("email_digest_hour", Number(v))}
          disabled={!enabled}
        >
          {HOURS.map((h) => (
            <Option key={h} value={String(h)}>
              {String(h).padStart(2, "0")}:00
            </Option>
          ))}
        </Select>
      </SettingsRow>
    </>
  );
}
