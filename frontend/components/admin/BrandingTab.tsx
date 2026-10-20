"use client";
/**
 * @file components/admin/BrandingTab.tsx
 * @brief Admin branding editor: name, tagline, accent color (AA-checked).
 */
import { useState } from "react";
import { Button, Input } from "@/components/ui";
import { useBranding, useUpdateBranding } from "@/hooks/useBranding";
import { accentPassesAA, type Branding } from "@/lib/api/branding";
import { formatApiError } from "@/lib/api/errors";
import { AdminLoading, AdminNotice } from "./AdminState";

const ACCENT_ERROR =
  "Accent needs at least 4.5:1 contrast with the dark green text.";

function BrandingForm({ initial }: { initial: Branding }) {
  const update = useUpdateBranding();
  const [name, setName] = useState(initial.community_name);
  const [tagline, setTagline] = useState(initial.tagline ?? "");
  const [accent, setAccent] = useState(initial.color_accent);
  const [serverError, setServerError] = useState<string | null>(null);

  const accentError = accentPassesAA(accent) ? undefined : ACCENT_ERROR;
  const canSave = !accentError && name.trim().length > 0 && !update.isPending;

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSave) return;
    setServerError(null);
    update.mutate(
      { community_name: name.trim(), tagline, color_accent: accent },
      { onError: (err) => setServerError(formatApiError(err)) },
    );
  };

  return (
    <form onSubmit={submit} className="flex max-w-md flex-col gap-4">
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
      <div className="flex items-end gap-3">
        <input
          type="color"
          aria-label="Accent color picker"
          value={accentPassesAA(accent) ? accent : "#c6b4f5"}
          onChange={(e) => setAccent(e.target.value)}
          className="size-11 shrink-0 cursor-pointer rounded-xl"
        />
        <div className="flex-1">
          <Input
            label="Accent color"
            value={accent}
            maxLength={7}
            error={accentError}
            hint="Hex, for example #C6B4F5"
            onChange={(e) => setAccent(e.target.value)}
          />
        </div>
      </div>
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
