"use client";
/**
 * @file components/admin/BrandingExtraFields.tsx
 * @brief Email, landing page and PWA icon fields for the branding form.
 */
import { Input, Switch } from "@/components/ui";
import type { Branding } from "@/lib/api/branding";

export const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export interface ExtraValues {
  email_logo_media_id: string;
  email_footer_text: string;
  email_sender_name: string;
  landing_cta_text: string;
  landing_show_feature_list: boolean;
  pwa_icon_192_media_id: string;
  pwa_icon_512_media_id: string;
}

/**
 * @brief Initial extra-field values from stored branding.
 * @param b stored branding
 */
export function extraInitial(b: Branding): ExtraValues {
  return {
    email_logo_media_id: b.email_logo_media_id ?? "",
    email_footer_text: b.email_footer_text ?? "",
    email_sender_name: b.email_sender_name ?? "",
    landing_cta_text: b.landing_cta_text ?? "",
    landing_show_feature_list: b.landing_show_feature_list ?? true,
    pwa_icon_192_media_id: b.pwa_icon_192_media_id ?? "",
    pwa_icon_512_media_id: b.pwa_icon_512_media_id ?? "",
  };
}

const MEDIA: [keyof ExtraValues, string][] = [
  ["email_logo_media_id", "Email logo media ID"],
  ["pwa_icon_192_media_id", "PWA icon 192x192 media ID"],
  ["pwa_icon_512_media_id", "PWA icon 512x512 media ID"],
];
const TEXT: [keyof ExtraValues, string, number][] = [
  ["email_footer_text", "Email footer text", 300],
  ["email_sender_name", "Email sender name", 100],
  ["landing_cta_text", "Landing CTA text", 200],
];

/**
 * @brief Whether every media ID is empty or a valid UUID.
 * @param v extra values
 */
export const extraValid = (v: ExtraValues) =>
  MEDIA.every(([k]) => !v[k] || UUID_RE.test(v[k] as string));

/**
 * @brief Request body containing only the changed extra fields.
 * @param v current values
 * @param init initial values
 */
export function extraChanges(v: ExtraValues, init: ExtraValues) {
  return Object.fromEntries(
    (Object.keys(v) as (keyof ExtraValues)[])
      .filter((k) => v[k] !== init[k])
      .map((k) => [k, v[k]]),
  );
}

/**
 * @brief Render the extra branding inputs.
 * @param value current values
 * @param onChange change handler
 */
export function BrandingExtraFields({
  value,
  onChange,
}: {
  value: ExtraValues;
  onChange: (v: ExtraValues) => void;
}) {
  const set = (p: Partial<ExtraValues>) => onChange({ ...value, ...p });
  return (
    <>
      {MEDIA.map(([k, label]) => (
        <Input
          key={k}
          label={label}
          value={value[k] as string}
          placeholder="UUID of an uploaded media item"
          error={
            value[k] && !UUID_RE.test(value[k] as string)
              ? "Enter a valid media UUID."
              : undefined
          }
          onChange={(e) => set({ [k]: e.target.value.trim() })}
        />
      ))}
      {TEXT.map(([k, label, max]) => (
        <Input
          key={k}
          label={label}
          value={value[k] as string}
          maxLength={max}
          onChange={(e) => set({ [k]: e.target.value })}
        />
      ))}
      <label className="flex items-center gap-3 text-sm">
        <Switch
          checked={value.landing_show_feature_list}
          onCheckedChange={(c) => set({ landing_show_feature_list: c })}
        />
        Show feature list on landing page
      </label>
    </>
  );
}
