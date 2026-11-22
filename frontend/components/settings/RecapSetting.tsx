"use client";
/**
 * @file components/settings/RecapSetting.tsx
 * @brief Radio group for the family recap email cadence.
 */
import { useTranslations } from "next-intl";
import type { RecapCadence } from "@/lib/notifications/types";

const OPTIONS: RecapCadence[] = ["weekly", "monthly", "off"];

/**
 * @brief Weekly / Monthly / Off picker.
 * @param props value: current cadence; onChange: called with the new cadence
 * @return fieldset of native radios (keyboard and screen-reader friendly)
 */
export function RecapSetting({
  value,
  onChange,
}: {
  value: RecapCadence;
  onChange: (next: RecapCadence) => void;
}) {
  const t = useTranslations("settings.notif");
  return (
    <fieldset className="flex flex-col gap-2">
      <legend className="mb-1 text-sm text-muted-foreground">
        {t("recap_hint")}
      </legend>
      {OPTIONS.map((opt) => (
        <label key={opt} className="flex items-center gap-2 text-sm">
          <input
            type="radio"
            name="recap_cadence"
            value={opt}
            checked={value === opt}
            onChange={() => onChange(opt)}
            className="size-4 accent-primary focus-visible:outline-2 focus-visible:outline-offset-2"
          />
          {t(`recap_${opt}`)}
        </label>
      ))}
    </fieldset>
  );
}
