"use client";
/**
 * @file components/admin/BrandingTab.tsx
 * @brief Admin branding editor: name, tagline, 7-color palette, fonts, live preview.
 */
import { useState } from "react";
import { Button, Input } from "@/components/ui";
import { useBranding, useUpdateBranding } from "@/hooks/useBranding";
import { accentPassesAA, type Branding } from "@/lib/api/branding";
import { formatApiError } from "@/lib/api/errors";
import {
  COLOR_FIELDS,
  HEX_RE,
  checkPairs,
  type ColorKey,
} from "@/lib/branding-palette";
import { BrandingPreview } from "./BrandingPreview";
import { ColorPicker } from "./ColorPicker";
import { FontPicker } from "./FontPicker";
import { AdminLoading, AdminNotice } from "./AdminState";

const ACCENT_ERROR =
  "Accent needs at least 4.5:1 contrast with the dark green text.";

function BrandingForm({ initial }: { initial: Branding }) {
  const update = useUpdateBranding();
  const [name, setName] = useState(initial.community_name);
  const [tagline, setTagline] = useState(initial.tagline ?? "");
  const init = Object.fromEntries(
    COLOR_FIELDS.map((f) => [f.key, initial[f.key] ?? f.def]),
  ) as Record<ColorKey, string>;
  const [colors, setColors] = useState(init);
  const [font, setFont] = useState(initial.font_family ?? "Inter");
  const [mono, setMono] = useState(
    initial.font_family_mono ?? "JetBrains Mono",
  );
  const [serverError, setServerError] = useState<string | null>(null);

  const changed = COLOR_FIELDS.filter(
    ({ key }) => colors[key].toLowerCase() !== init[key].toLowerCase(),
  ).map((f) => f.key);
  // Only changed colors are validated/sent, so legacy values never block saves.
  const invalid = changed.some((k) => !HEX_RE.test(colors[k]));
  const accentError =
    changed.includes("color_accent") && !accentPassesAA(colors.color_accent)
      ? ACCENT_ERROR
      : undefined;
  const canSave =
    !accentError && !invalid && name.trim().length > 0 && !update.isPending;
  const warnings = checkPairs(colors).filter((p) => !p.ok);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSave) return;
    setServerError(null);
    update.mutate(
      {
        community_name: name.trim(),
        tagline,
        ...Object.fromEntries(changed.map((k) => [k, colors[k]])),
        ...(font !== (initial.font_family ?? "Inter")
          ? { font_family: font }
          : {}),
        ...(mono !== (initial.font_family_mono ?? "JetBrains Mono")
          ? { font_family_mono: mono }
          : {}),
      },
      { onError: (err) => setServerError(formatApiError(err)) },
    );
  };

  return (
    <form onSubmit={submit} className="flex flex-col gap-6">
      <div className="flex max-w-md flex-col gap-4">
        <Input
          label="Community name"
          value={name}
          maxLength={100}
          onChange={(e) => setName(e.target.value)}
        />
        <Input
          label="Tagline"
          value={tagline}
          maxLength={300}
          onChange={(e) => setTagline(e.target.value)}
        />
        {COLOR_FIELDS.map(({ key, label }) => (
          <ColorPicker
            key={key}
            label={label}
            value={colors[key]}
            error={key === "color_accent" ? accentError : undefined}
            onChange={(v) => setColors((c) => ({ ...c, [key]: v }))}
          />
        ))}
        <FontPicker
          label="Font family"
          kind="sans"
          value={font}
          onChange={setFont}
        />
        <FontPicker
          label="Monospace font"
          kind="mono"
          value={mono}
          onChange={setMono}
        />
      </div>
      {warnings.map((w) => (
        <p key={w.id} role="status" className="text-sm text-amber-700">
          {w.label}: {w.ratio.toFixed(2)}:1 is below {w.min}:1 (warning only).
        </p>
      ))}
      <BrandingPreview colors={colors} font={font} mono={mono} />
      {serverError && <AdminNotice tone="error">{serverError}</AdminNotice>}
      <div>
        <Button type="submit" disabled={!canSave}>
          Save branding
        </Button>
      </div>
    </form>
  );
}

/**
 * @brief Branding tab.
 * @return loading, error, or form
 */
export function BrandingTab() {
  const { data, isLoading, error } = useBranding();
  if (isLoading) return <AdminLoading />;
  if (error || !data)
    return <AdminNotice tone="error">Failed to load branding.</AdminNotice>;
  return <BrandingForm initial={data} />;
}
