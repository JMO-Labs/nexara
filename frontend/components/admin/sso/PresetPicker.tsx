"use client";
/**
 * @file components/admin/sso/PresetPicker.tsx
 * @brief SSO wizard step 1: choose a provider preset (radio cards).
 */
import type { OAuthPreset } from "@/lib/api/adminOauth";
import { cn } from "@/lib/utils";

/**
 * @brief Fill a preset discovery URL template ("{host}", "{slug}", ...).
 * @param template URL template from the preset
 * @param values admin-entered placeholder values (defaults fill gaps)
 * @return URL, or null while a placeholder is still empty
 */
export function renderDiscoveryUrl(
  template: string | null,
  values: Record<string, string>,
): string | null {
  if (!template) return null;
  let missing = false;
  const url = template.replace(/\{(\w+)\}/g, (_m, name: string) => {
    const v = (values[name] ?? "").trim();
    if (!v) missing = true;
    return v;
  });
  return missing ? null : url;
}

/** @brief Props for PresetPicker. */
export interface PresetPickerProps {
  presets: OAuthPreset[];
  value: string | null;
  onChange: (key: string) => void;
}

/**
 * @brief Radio group of presets; help text of the chosen one is shown below.
 * @param props see PresetPickerProps
 * @return radio group
 */
export function PresetPicker({ presets, value, onChange }: PresetPickerProps) {
  const chosen = presets.find((p) => p.key === value);
  return (
    <div className="flex flex-col gap-3">
      <div
        role="radiogroup"
        aria-label="Provider preset"
        className="grid grid-cols-2 gap-2 sm:grid-cols-3"
      >
        {presets.map((p) => {
          const checked = p.key === value;
          return (
            <label
              key={p.key}
              className={cn(
                "glass-item flex min-h-11 cursor-pointer items-center gap-2 rounded-2xl px-3 py-2 text-sm focus-within:ring-2 focus-within:ring-[var(--nx-blue)]",
                checked && "ring-2 ring-[var(--nx-blue)]",
              )}
            >
              <input
                type="radio"
                name="sso-preset"
                value={p.key}
                checked={checked}
                onChange={() => onChange(p.key)}
                className="size-4 accent-[var(--nx-blue)]"
              />
              <span className="font-medium">{p.label}</span>
              <span className="ml-auto text-xs text-muted">
                {p.kind === "oidc" ? "OIDC" : "OAuth2"}
              </span>
            </label>
          );
        })}
      </div>
      {chosen && <p className="text-sm text-muted">{chosen.help}</p>}
    </div>
  );
}
